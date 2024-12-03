import datetime
import logging
import os
import pathlib
import re
import subprocess

import boto3
from tenacity import retry, stop_after_attempt, wait_fixed

from pg_dumper.config import Config, Storage, Target

logger = logging.getLogger("pg_dumper")


def make_backup_filename(target: Target):
    return f"{target.name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.bkp"


def take_pg_dump(target: Target, config: Config):
    work_dir = pathlib.Path(config.workingDir).joinpath(target.name)
    work_dir.mkdir(exist_ok=True)

    filename = make_backup_filename(target)
    filepath = work_dir.joinpath(filename)

    # fmt: off
    command = [
        "pg_dump", "-Fc",
        "-d", target.database,
        "-h", target.host,
        "-p", str(target.port),
        "-U", target.username,
        "-f", str(filepath),
    ]
    # fmt: on

    env = os.environ.copy()
    env["PGPASSWORD"] = target.password
    logger.info(f"Running command: {' '.join(command)}")

    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode == 0:
        logger.info(f"Dump successful. {result.stdout}")
    else:
        logger.error(result.stderr)
        raise ValueError("Error running pg_dump")

    return filepath


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def upload_file_to_s3(filepath: str, target: Target, config: Config):
    storage = next(storage for storage in config.storages if storage.name == target.storage)
    session = boto3.Session(
        aws_access_key_id=storage.accessKey,
        aws_secret_access_key=storage.secretKey,
    )
    s3 = session.client("s3", endpoint_url=storage.endpoint)
    filename = os.path.basename(filepath)

    logger.info(f"Uploading {filename} to {storage.bucket}/{target.name}/{filename}")
    s3.upload_file(filepath, storage.bucket, f"{target.name}/{filename}")
    logger.info("Upload successful")


def run_backup(target: Target, config: Config):
    filepath = take_pg_dump(target, config)
    upload_file_to_s3(filepath, target, config)
    logger.debug(f"Removing {filepath}")
    os.remove(filepath)


def get_created_date(filename: str) -> datetime.datetime | None:
    match = re.match(r".*_(\d{14})\.bkp", filename)
    if match:
        return datetime.datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    return None


def clean_target(target: Target, storage: Storage):
    logger.info(f"Cleaning up {target.name}")
    session = boto3.Session(
        aws_access_key_id=storage.accessKey,
        aws_secret_access_key=storage.secretKey,
    )
    s3 = session.client("s3", endpoint_url=storage.endpoint)
    respose = s3.list_objects_v2(Bucket=storage.bucket, Prefix=f"{target.name}/")

    files = []
    for obj in respose.get("Contents", []):
        filename = obj["Key"]
        created_date = get_created_date(filename)
        if created_date:
            logger.debug(f"Found file {filename} created at {created_date} for target {target.name}")
            files.append((filename, created_date))

    files = sorted(files, key=lambda x: x[1], reverse=True)
    files = files[target.minRetention :]

    for filename, date in files:
        if date < datetime.datetime.now() - datetime.timedelta(days=target.expireAfterDays):
            s3.delete_object(Bucket=storage.bucket, Key=filename)
            logger.info(f"Deleting {filename}")


def run_cleanup(config: Config):
    for target in config.targets:
        storage = next(storage for storage in config.storages if storage.name == target.storage)
        clean_target(target, storage)
