import pytest

from src.api.storage import MemoryStorage

EXPECTED_COUNT = 2
EXPECTED_DURATION_MS = 25
EXPECTED_REPORT_DURATION_MS = 15


@pytest.fixture
def storage():
    return MemoryStorage()


def test_add_session(storage):
    session = storage.add_session(
        locale="ru",
        user_agent="pytest",
    )

    assert session["id"] == 1
    assert session["locale"] == "ru"
    assert session["user_agent"] == "pytest"


def test_scan_sessions(storage):
    storage.add_session(locale="ru")
    storage.add_session(locale="en")

    sessions = storage.scan_sessions()

    assert len(sessions) == EXPECTED_COUNT


def test_get_session(storage):
    session = storage.add_session(locale="ru")

    result = storage.get_session(session["id"])

    assert result == session


def test_edit_session(storage):
    session = storage.add_session(locale="ru")

    updated = storage.edit_session(
        session["id"],
        locale="en",
    )

    assert updated["locale"] == "en"


def test_add_instruction(storage):
    session = storage.add_session()

    instruction = storage.add_instruction(
        session_id=session["id"],
        argument="examples/red_square.gif",
        tags="test",
    )

    assert instruction["id"] == 1
    assert instruction["session"] == session["id"]


def test_instruction_requires_session(storage):
    with pytest.raises(ValueError):
        storage.add_instruction(
            session_id=999,
            argument="test.gif",
        )


def test_scan_instructions(storage):
    session = storage.add_session()

    storage.add_instruction(
        session["id"],
        "first.gif",
    )

    storage.add_instruction(
        session["id"],
        "second.gif",
    )

    result = storage.scan_instructions(session["id"])

    assert len(result) == EXPECTED_COUNT


def test_edit_instruction(storage):
    session = storage.add_session()

    instruction = storage.add_instruction(
        session["id"],
        "old.gif",
    )

    updated = storage.edit_instruction(
        instruction["id"],
        argument="new.gif",
    )

    assert updated["argument"] == "new.gif"


def test_add_completion(storage):
    session = storage.add_session()

    instruction = storage.add_instruction(
        session["id"],
        "example.gif",
    )

    completion = storage.add_completion(
        instruction["id"],
        result="result.png",
        stage="completed",
        duration=25,
    )

    assert completion["stage"] == "completed"
    assert completion["duration"] == EXPECTED_DURATION_MS


def test_completion_requires_instruction(storage):
    with pytest.raises(ValueError):
        storage.add_completion(
            instruction_id=999,
        )


def test_scan_completions(storage):
    session = storage.add_session()

    instruction = storage.add_instruction(
        session["id"],
        "example.gif",
    )

    storage.add_completion(instruction["id"])
    storage.add_completion(instruction["id"])

    result = storage.scan_completions(instruction["id"])

    assert len(result) == EXPECTED_COUNT


def test_report_scan(storage):
    session = storage.add_session()

    instruction = storage.add_instruction(
        session["id"],
        "example.gif",
        tags="conversion",
    )

    storage.add_completion(
        instruction["id"],
        result="result.png",
        stage="completed",
        duration=15,
    )

    report = storage.report_scan()

    assert len(report) == 1
    assert report[0]["duration"] == EXPECTED_REPORT_DURATION_MS
    assert report[0]["result"] == "result.png"
    assert report[0]["tags"] == "conversion"
