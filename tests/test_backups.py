from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pg_dumper.backup import take_pg_dump
from pg_dumper.config import Config, Target


@pytest.fixture
def test_config():
    return Config(storages=[], targets=[], workingDir="/tmp/test", logLevel="INFO")


@pytest.fixture
def test_target():
    return Target(
        name="test-db",
        host="localhost",
        port=5432,
        username="test_user",
        password="test_pass",
        database="test_db",
        schedule="0 0 * * *",
        storage="test-storage",
        expireAfterDays=7,
        minRetention=1,
    )


def test_take_pg_dump_success(test_config, test_target):
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.mkdir") as mock_mkdir:
        # Setup mock successful response
        mock_run.return_value = MagicMock(returncode=0, stdout="Backup successful", stderr="")

        # Run the function
        result = take_pg_dump(test_target, test_config)

        # Verify directory creation
        mock_mkdir.assert_called_once_with(exist_ok=True)

        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        command = args[0]

        assert command[0] == "pg_dump"
        assert command[1] == "-Fc"
        assert "-d" in command and command[command.index("-d") + 1] == "test_db"
        assert "-h" in command and command[command.index("-h") + 1] == "localhost"
        assert "-p" in command and command[command.index("-p") + 1] == "5432"
        assert "-U" in command and command[command.index("-U") + 1] == "test_user"

        # Verify environment variables
        assert kwargs["env"]["PGPASSWORD"] == "test_pass"

        # Verify result is a path
        assert isinstance(result, Path)
        assert str(result).startswith("/tmp/test/test-db")
        assert str(result).endswith(".bkp")


def test_take_pg_dump_failure(test_config, test_target):
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.mkdir"):
        # Setup mock failure response
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: connection failed")

        # Verify the function raises ValueError
        with pytest.raises(ValueError, match="Error running pg_dump"):
            take_pg_dump(test_target, test_config)


def test_take_pg_dump_creates_directory(test_config, test_target):
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.mkdir") as mock_mkdir:
        mock_run.return_value = MagicMock(returncode=0, stdout="Backup successful", stderr="")

        take_pg_dump(test_target, test_config)

        # Verify directory creation
        expected_dir = Path("/tmp/test").joinpath("test-db")
        mock_mkdir.assert_called_once_with(exist_ok=True)


def test_take_pg_dump_filename_format(test_config, test_target):
    with patch("subprocess.run") as mock_run, patch("pathlib.Path.mkdir"), patch("datetime.datetime") as mock_datetime:
        # Mock datetime to have a fixed value
        mock_datetime.now.return_value.strftime.return_value = "20230101120000"

        mock_run.return_value = MagicMock(returncode=0, stdout="Backup successful", stderr="")

        result = take_pg_dump(test_target, test_config)

        # Verify filename format
        assert str(result).endswith("test-db_20230101120000.bkp")
