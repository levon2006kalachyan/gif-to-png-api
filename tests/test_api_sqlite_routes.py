import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer

import pytest

from src.api.client import APIClient
from src.api.server import APIHandler
from src.api.sqlite_storage import SQLiteStorage
from src.api.worker import ConversionWorker


def create_client(server):
    host, port = server.server_address
    return APIClient(
        base_url=f"http://{host}:{port}",
        username="test",
        password="test123",
    )


@pytest.fixture
def sqlite_api(tmp_path):
    storage = SQLiteStorage(tmp_path / "routes.db")

    class SQLiteHandler(APIHandler):
        pass

    SQLiteHandler.username = "test"
    SQLiteHandler.password = "test123"
    SQLiteHandler.storage = storage
    SQLiteHandler.worker = ConversionWorker(storage, test_mode=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), SQLiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield create_client(server)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        storage.close()


def prepare_route_data(client):
    session = client.session_add(locale="ru", user_agent="pytest")
    assert session["http_status"] == HTTPStatus.OK
    session_id = int(session["data"]["id"])

    instruction = client.instruction_add(
        session_id,
        "examples/red_square.gif",
        "test",
    )
    assert instruction["http_status"] == HTTPStatus.OK

    instruction_id = int(instruction["data"]["id"])
    completion_id = int(instruction["data"]["completion_id"])
    return session_id, instruction_id, completion_id


def build_route_operations(client, session_id, instruction_id, completion_id):
    return {
        "session-add": lambda: client.session_add(
            locale="en", user_agent="route-test"
        ),
        "session-scan": client.session_scan,
        "session-single": lambda: client.session_single(session_id),
        "session-edit": lambda: client.session_edit(session_id, locale="de"),
        "instruction-add": lambda: client.instruction_add(
            session_id, "examples/blue_circle.gif", "blue"
        ),
        "instruction-scan": lambda: client.instruction_scan(session_id),
        "instruction-single": lambda: client.instruction_single(instruction_id),
        "instruction-edit": lambda: client.instruction_edit(
            instruction_id, tags="updated"
        ),
        "completion-scan": lambda: client.completion_scan(instruction_id),
        "completion-single": lambda: client.completion_single(completion_id),
        "report-scan": client.report_scan,
    }


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
    session_id, instruction_id, completion_id = prepare_route_data(client)

    operations = build_route_operations(
        client, session_id, instruction_id, completion_id
    )
    response = operations[route]()

    assert response["http_status"] == HTTPStatus.OK
    assert response["status"] == "success"
