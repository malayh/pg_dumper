import os
import yaml
import logging
from pydantic import BaseModel
import boto3
from multiprocessing import Value

logger = logging.getLogger("pg_dumper")

class Storage(BaseModel):
    name: str
    endpoint: str
    accessKey: str
    secretKey: str
    bucket: str

class Target(BaseModel):
    name: str
    host: str
    port: int
    username: str
    password: str
    database: str
    schedule: str
    storage: str

class Config(BaseModel):
    storages: list[Storage]
    targets: list[Target]
    workingDir: str
    logLevel: str

    @classmethod
    def from_config_file(cls, config_file_path: str):
        logger.info(f"Reading config from {config_file_path}")
        with open(config_file_path, 'r') as f:
            config_file = yaml.safe_load(f)
            _config = Config(**config_file)
            verify_config(_config)
            logger.info(f"Config: {_config}")
        
        return _config


def verify_storage_config(storages: list[Storage]):
    for storage in storages:
        logger.info(f"Verifying storage {storage.name}")
        session = boto3.Session(
            aws_access_key_id=storage.accessKey,
            aws_secret_access_key=storage.secretKey,
        )
        s3 = session.client("s3", endpoint_url=storage.endpoint)
        s3.head_bucket(Bucket=storage.bucket)


def verify_config(config: Config):
    # Veirfy target names are unique
    target_names = [target.name for target in config.targets]
    if len(target_names) != len(set(target_names)):
        raise ValueError("Target names must be unique")
    
    # Verify storage names are unique
    storage_names = [storage.name for storage in config.storages]
    if len(storage_names) != len(set(storage_names)):
        raise ValueError("Storage names must be unique")
    
    # verify storage names are valid
    for target in config.targets:
        if target.storage not in storage_names:
            raise ValueError(f"Storage {target.storage} not found in storages")
                
    # Verify logLevel is valid
    valid_log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
    if config.logLevel not in valid_log_levels:
        raise ValueError(f"Invalid log level: {config.logLevel}. Must be one of {valid_log_levels}")


    # Verify workingDir exists and is a directory
    if not os.path.isdir(config.workingDir):
        raise ValueError(f"Working directory {config.workingDir} does not exist or is not a directory")
    

    verify_storage_config(config.storages)
     
