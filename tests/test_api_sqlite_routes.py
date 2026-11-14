
import threading
from http.server import ThreadingHTTPServer

import pytest

from src.api.client import APIClient
from src.api.server import APIHandler
from src.api.sqlite_storage import SQLiteStorage
from src.api.worker import ConversionWorker


@pytest.fixture
def sqlite_api(tmp_path):
    storage = SQLiteStorage(tmp_path / "routes.db")

    class SQLiteHandler(APIHandler):
        pass

    SQLiteHandler.username = "test"
    SQLiteHandler.password = "test123"
    SQLiteHandler.storage = storage
    SQLiteHandler.worker = ConversionWorker(
        storage,
        test_mode=True,
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        SQLiteHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    host, port = server.server_address

    client = APIClient(
        base_url=f"http://{host}:{port}",
        username="test",
        password="test123",
    )

    try:
        yield client
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        storage.close()


@pytest.mark.parametrize(
    "route",
    [
        "session-add",
        "session-scan",
        "session-single",
        "session-edit",
        "instruction-add",
        "instruction-scan",
        "instruction-single",
        "instruction-edit",
        "completion-scan",
        "completion-single",
        "report-scan",
    ],
)
def test_sqlite_api_routes(sqlite_api, route):
    client = sqlite_api

    session = client.session_add(
        locale="ru",
        user_agent="pytest",
    )
    assert session["http_status"] == 200
    session_id = int(session["data"]["id"])

    instruction = client.instruction_add(
        session_id,
        "examples/red_square.gif",
        "test",
    )
    assert instruction["http_status"] == 200

    instruction_id = int(instruction["data"]["id"])
    completion_id = int(
        instruction["data"]["completion_id"]
    )

    operations = {
        "session-add": lambda: client.session_add(
            locale="en",
            user_agent="route-test",
        ),
        "session-scan": client.session_scan,
        "session-single": lambda: client.session_single(
            session_id
        ),
        "session-edit": lambda: client.session_edit(
            session_id,
            locale="de",
        ),
        "instruction-add": lambda: client.instruction_add(
            session_id,
            "examples/blue_circle.gif",
            "blue",
        ),
        "instruction-scan": lambda: client.instruction_scan(
            session_id
        ),
        "instruction-single": lambda: client.instruction_single(
            instruction_id
        ),
        "instruction-edit": lambda: client.instruction_edit(
            instruction_id,
            tags="updated",
        ),
        "completion-scan": lambda: client.completion_scan(
            instruction_id
        ),
        "completion-single": lambda: client.completion_single(
            completion_id
        ),
        "report-scan": client.report_scan,
    }

    response = operations[route]()

    assert response["http_status"] == 200
    assert response["status"] == "success"

