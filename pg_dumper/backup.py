import datetime
import logging
import os
import pathlib
import subprocess

import boto3
from tenacity import retry, stop_after_attempt, wait_fixed

from pg_dumper.config import Config, Target

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
