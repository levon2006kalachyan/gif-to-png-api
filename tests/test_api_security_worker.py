import base64
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.api.auth import check_basic_auth
from src.api.storage import MemoryStorage
from src.api.worker import ConversionWorker


@given(
    username=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz",
        min_size=1,
        max_size=15,
    ),
    password=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=1,
        max_size=15,
    ),
)
@settings(max_examples=30)
def test_valid_basic_auth(username, password):
    credentials = username + ":" + password

    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")

    header = f"Basic {encoded}"

    assert check_basic_auth(
        header,
        username,
        password,
    )


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "Bearer token",
        "Basic invalid!!!",
        "Basic",
        "Basic !!!",
        "Basic " + base64.b64encode(b"invalidcredentials").decode("ascii"),
    ],
)
def test_invalid_basic_auth(header):
    assert not check_basic_auth(
        header,
        "admin",
        "admin123",
    )


def test_wrong_basic_auth_password():
    encoded = base64.b64encode(b"admin:wrongpassword").decode("ascii")

    assert not check_basic_auth(
        f"Basic {encoded}",
        "admin",
        "admin123",
    )


@pytest.fixture
def storage_with_instruction():
    storage = MemoryStorage()

    session = storage.add_session(
        locale="ru",
        user_agent="pytest",
    )

    instruction = storage.add_instruction(
        session_id=session["id"],
        argument="examples/red_square.gif",
        tags="test",
    )

    return storage, instruction


def wait_for_completion(storage, completion_id):
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        completion = storage.get_completion(completion_id)

        if completion["stage"] in (
            "completed",
            "failed",
        ):
            return completion

        time.sleep(0.01)

    pytest.fail("Worker did not finish within 10 seconds")


def test_worker_test_mode(storage_with_instruction):
    storage, instruction = storage_with_instruction

    worker = ConversionWorker(
        storage,
        test_mode=True,
    )

    completion = worker.start(instruction)

    result = wait_for_completion(
        storage,
        completion["id"],
    )

    assert result["stage"] == "completed"
    assert result["result"].endswith(".png")
    assert result["failure"] == ""


def test_worker_real_conversion(
    storage_with_instruction,
    tmp_path,
):
    storage, instruction = storage_with_instruction

    worker = ConversionWorker(
        storage,
        test_mode=False,
    )

    with patch(
        "src.api.worker.OUTPUT_DIR",
        tmp_path,
    ):
        completion = worker.start(instruction)

        result = wait_for_completion(
            storage,
            completion["id"],
        )

    assert result["stage"] == "completed"

    output_path = Path(result["result"])

    assert output_path.is_file()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_worker_subprocess_error(
    storage_with_instruction,
    tmp_path,
):
    storage, instruction = storage_with_instruction

    worker = ConversionWorker(
        storage,
        test_mode=False,
    )

    fake_process = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="Conversion failed",
    )

    with (
        patch(
            "src.api.worker.OUTPUT_DIR",
            tmp_path,
        ),
        patch(
            "src.api.worker.subprocess.run",
            return_value=fake_process,
        ),
    ):
        completion = worker.start(instruction)

        result = wait_for_completion(
            storage,
            completion["id"],
        )

    assert result["stage"] == "failed"
    assert "Conversion failed" in result["failure"]


def test_worker_timeout(
    storage_with_instruction,
    tmp_path,
):
    storage, instruction = storage_with_instruction

    worker = ConversionWorker(
        storage,
        test_mode=False,
    )

    with (
        patch(
            "src.api.worker.OUTPUT_DIR",
            tmp_path,
        ),
        patch(
            "src.api.worker.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["python"],
                timeout=60,
            ),
        ),
    ):
        completion = worker.start(instruction)

        result = wait_for_completion(
            storage,
            completion["id"],
        )

    assert result["stage"] == "failed"
    assert result["failure"]


def test_worker_missing_output(
    storage_with_instruction,
    tmp_path,
):
    storage, instruction = storage_with_instruction

    worker = ConversionWorker(
        storage,
        test_mode=False,
    )

    fake_process = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="SUCCESS",
        stderr="",
    )

    with (
        patch(
            "src.api.worker.OUTPUT_DIR",
            tmp_path,
        ),
        patch(
            "src.api.worker.subprocess.run",
            return_value=fake_process,
        ),
    ):
        completion = worker.start(instruction)

        result = wait_for_completion(
            storage,
            completion["id"],
        )

    assert result["stage"] == "failed"
    assert "PNG output file was not created" in result["failure"]
