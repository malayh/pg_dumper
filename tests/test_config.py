import os
from unittest.mock import MagicMock, patch

import pytest

from pg_dumper.config import Config, Storage, Target, verify_config


def test_config_valid():
    # Mock boto3.Session and its chain of calls
    with patch("boto3.Session") as mock_session:
        # Setup mock chain
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Test configuration
        config = Config(
            storages=[
                Storage(
                    name="test-storage",
                    endpoint="http://localhost:9000",
                    accessKey="access-key",
                    secretKey="secret-key",
                    bucket="test-bucket",
                )
            ],
            targets=[
                Target(
                    name="test-target",
                    host="localhost",
                    port=5432,
                    username="postgres",
                    password="postgres",
                    database="test",
                    schedule="0 0 * * *",
                    storage="test-storage",
                    expireAfterDays=7,
                    minRetention=1,
                )
            ],
            workingDir="/tmp",
            logLevel="INFO",
        )

        # Verify configuration
        verify_config(config)

        # Verify mocks were called correctly
        mock_session.assert_called_once_with(aws_access_key_id="access-key", aws_secret_access_key="secret-key")
        mock_session.return_value.client.assert_called_once_with("s3", endpoint_url="http://localhost:9000")
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")


def test_duplicate_target_names():
    with pytest.raises(ValueError, match="Target names must be unique"):
        config = Config(
            storages=[
                Storage(
                    name="test-storage",
                    endpoint="http://localhost:9000",
                    accessKey="access-key",
                    secretKey="secret-key",
                    bucket="test-bucket",
                )
            ],
            targets=[
                Target(
                    name="test-target",
                    host="localhost",
                    port=5432,
                    username="postgres",
                    password="postgres",
                    database="test1",
                    schedule="0 0 * * *",
                    storage="test-storage",
                    expireAfterDays=7,
                    minRetention=1,
                ),
                Target(
                    name="test-target",  # Duplicate name
                    host="localhost",
                    port=5432,
                    username="postgres",
                    password="postgres",
                    database="test2",
                    schedule="0 0 * * *",
                    storage="test-storage",
                    expireAfterDays=7,
                    minRetention=1,
                ),
            ],
            workingDir="/tmp",
            logLevel="INFO",
        )
        verify_config(config)


def test_duplicate_storage_names():
    with pytest.raises(ValueError, match="Storage names must be unique"):
        config = Config(
            storages=[
                Storage(
                    name="test-storage",
                    endpoint="http://localhost:9000",
                    accessKey="access-key",
                    secretKey="secret-key",
                    bucket="test-bucket1",
                ),
                Storage(
                    name="test-storage",  # Duplicate name
                    endpoint="http://localhost:9000",
                    accessKey="access-key",
                    secretKey="secret-key",
                    bucket="test-bucket2",
                ),
            ],
            targets=[],
            workingDir="/tmp",
            logLevel="INFO",
        )
        verify_config(config)


def test_invalid_storage_reference():
    with pytest.raises(ValueError, match="Storage .* not found in storages"):
        config = Config(
            storages=[
                Storage(
                    name="test-storage",
                    endpoint="http://localhost:9000",
                    accessKey="access-key",
                    secretKey="secret-key",
                    bucket="test-bucket",
                )
            ],
            targets=[
                Target(
                    name="test-target",
                    host="localhost",
                    port=5432,
                    username="postgres",
                    password="postgres",
                    database="test",
                    schedule="0 0 * * *",
                    storage="non-existent-storage",  # Invalid storage reference
                    expireAfterDays=7,
                    minRetention=1,
                )
            ],
            workingDir="/tmp",
            logLevel="INFO",
        )
        verify_config(config)


def test_invalid_log_level():
    with pytest.raises(ValueError, match="Invalid log level"):
        config = Config(
            storages=[],
            targets=[],
            workingDir="/tmp",
            logLevel="INVALID",  # Invalid log level
        )
        verify_config(config)


def test_invalid_working_dir():
    with pytest.raises(ValueError, match="Working directory .* does not exist"):
        config = Config(storages=[], targets=[], workingDir="/non/existent/path", logLevel="INFO")
        verify_config(config)
