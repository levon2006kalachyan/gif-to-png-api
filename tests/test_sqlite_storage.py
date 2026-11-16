import pytest

from src.api.sqlite_storage import SQLiteStorage

EXPECTED_DURATION_MS = 250


@pytest.fixture
def storage(tmp_path):
    db = SQLiteStorage(tmp_path / "test.db")
    yield db
    db.close()


def test_session_crud(storage):
    assert storage.scan_sessions() == []
    assert storage.get_session(999999) is None
    assert storage.edit_session(999999, locale="en") is None

    session = storage.add_session(
        locale="ru",
        user_agent="pytest",
    )

    assert storage.get_session(session["id"])["locale"] == "ru"

    updated = storage.edit_session(
        session["id"],
        locale="en",
        user_agent="updated",
    )

    assert updated["locale"] == "en"
    assert updated["user_agent"] == "updated"
    assert len(storage.scan_sessions()) == 1


def test_instruction_crud(storage):
    assert storage.scan_instructions(999999) == []
    assert storage.get_instruction(999999) is None
    assert storage.edit_instruction(999999, tags="x") is None

    with pytest.raises(ValueError, match="Session not found"):
        storage.add_instruction(
            999999,
            "missing.gif",
        )

    session = storage.add_session(locale="ru")

    instruction = storage.add_instruction(
        session["id"],
        "examples/red_square.gif",
        tags="original",
    )

    updated = storage.edit_instruction(
        instruction["id"],
        argument="examples/blue_circle.gif",
        tags="updated",
    )

    assert updated["argument"] == "examples/blue_circle.gif"
    assert updated["tags"] == "updated"
    assert storage.get_instruction(instruction["id"]) == updated
    assert len(storage.scan_instructions(session["id"])) == 1


def test_completion_crud(storage):
    assert storage.scan_completions(999999) == []
    assert storage.get_completion(999999) is None
    assert storage.edit_completion(999999, stage="failed") is None

    with pytest.raises(ValueError, match="Instruction not found"):
        storage.add_completion(999999)

    session = storage.add_session()
    instruction = storage.add_instruction(
        session["id"],
        "examples/red_square.gif",
    )

    completion = storage.add_completion(
        instruction["id"],
    )

    updated = storage.edit_completion(
        completion["id"],
        result="output/test.png",
        stage="completed",
        failure="",
        cache_hit=1,
        duration=250,
    )

    assert updated["stage"] == "completed"
    assert updated["result"] == "output/test.png"
    assert updated["cache_hit"] == 1
    assert updated["duration"] == EXPECTED_DURATION_MS
    assert storage.get_completion(completion["id"]) == updated
    assert len(storage.scan_completions(instruction["id"])) == 1


def test_report_scan(storage):
    assert storage.report_scan() == []

    session = storage.add_session(locale="ru")
    instruction = storage.add_instruction(
        session["id"],
        "examples/red_square.gif",
        tags="report-test",
    )

    storage.add_completion(
        instruction["id"],
        result="output/report.png",
        stage="completed",
        duration=125,
    )

    report = storage.report_scan()

    assert len(report) == 1
    assert report[0] == {
        "duration": 125,
        "result": "output/report.png",
        "tags": "report-test",
    }


def test_sqlite_persistence(tmp_path):
    db_path = tmp_path / "persistent.db"

    first = SQLiteStorage(db_path)
    session = first.add_session(
        locale="ru",
        user_agent="persistence-test",
    )
    first.close()

    second = SQLiteStorage(db_path)

    try:
        saved = second.get_session(session["id"])
        assert saved["locale"] == "ru"
        assert saved["user_agent"] == "persistence-test"
    finally:
        second.close()
