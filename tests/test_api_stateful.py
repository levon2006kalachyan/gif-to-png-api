import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

from src.api.client import APIClient
from src.api.server import APIHandler
from src.api.storage import MemoryStorage
from src.api.worker import ConversionWorker


class APIStateMachine(RuleBasedStateMachine):
    """Модельное тестирование HTTP API."""

    def __init__(self):
        super().__init__()

        self.storage = MemoryStorage()

        class TestHandler(APIHandler):
            pass

        TestHandler.username = "test"
        TestHandler.password = "test123"
        TestHandler.storage = self.storage
        TestHandler.worker = ConversionWorker(
            self.storage,
            test_mode=True,
        )

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            TestHandler,
        )

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()

        host, port = self.server.server_address

        self.client = APIClient(
            base_url="http://{}:{}".format(host, port),
            username="test",
            password="test123",
        )

        self.sessions = {}
        self.instructions = {}
        self.completions = {}

    @initialize()
    def initialize_model(self):
        response = self.client.health()

        assert response["http_status"] == HTTPStatus.OK
        assert response["status"] == "success"

    @rule(
        locale=st.sampled_from(["ru", "en", "de", "fr"]),
        user_agent=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz",
            min_size=1,
            max_size=12,
        ),
    )
    def session_add(self, locale, user_agent):
        response = self.client.session_add(
            locale=locale,
            user_agent=user_agent,
        )

        assert response["http_status"] == HTTPStatus.OK

        session_id = int(response["data"]["id"])

        self.sessions[session_id] = {
            "locale": locale,
            "user_agent": user_agent,
        }

    @precondition(lambda self: bool(self.sessions))
    @rule(locale=st.sampled_from(["ru", "en", "es", "it"]))
    def session_edit(self, locale):
        session_id = next(iter(self.sessions))

        response = self.client.session_edit(
            session_id,
            locale=locale,
        )

        assert response["http_status"] == HTTPStatus.OK

        self.sessions[session_id]["locale"] = locale

    @precondition(lambda self: bool(self.sessions))
    @rule()
    def session_single(self):
        session_id = next(iter(self.sessions))

        response = self.client.session_single(session_id)

        assert response["http_status"] == HTTPStatus.OK

        expected = self.sessions[session_id]

        assert response["data"]["locale"] == expected["locale"]
        assert response["data"]["user_agent"] == expected["user_agent"]

    @rule()
    def session_scan(self):
        response = self.client.session_scan()

        assert response["http_status"] == HTTPStatus.OK
        assert int(response["data"]["count"]) == len(self.sessions)

    @precondition(lambda self: bool(self.sessions))
    @rule(
        argument=st.sampled_from(
            [
                "examples/red_square.gif",
                "examples/blue_circle.gif",
                "examples/green_triangle.gif",
                "missing.gif",
            ]
        ),
        tags=st.sampled_from(["red", "blue", "green", "test"]),
    )
    def instruction_add(self, argument, tags):
        session_id = next(iter(self.sessions))

        response = self.client.instruction_add(
            session_id,
            argument,
            tags,
        )

        assert response["http_status"] == HTTPStatus.OK

        instruction_id = int(response["data"]["id"])
        completion_id = int(response["data"]["completion_id"])

        self.instructions[instruction_id] = {
            "session": session_id,
            "argument": argument,
            "tags": tags,
        }

        self.completions[completion_id] = instruction_id

    @precondition(lambda self: bool(self.instructions))
    @rule(tags=st.sampled_from(["updated", "changed", "hypothesis"]))
    def instruction_edit(self, tags):
        instruction_id = next(iter(self.instructions))

        response = self.client.instruction_edit(
            instruction_id,
            tags=tags,
        )

        assert response["http_status"] == HTTPStatus.OK

        self.instructions[instruction_id]["tags"] = tags

    @precondition(lambda self: bool(self.instructions))
    @rule()
    def instruction_single(self):
        instruction_id = next(iter(self.instructions))

        response = self.client.instruction_single(instruction_id)

        assert response["http_status"] == HTTPStatus.OK

        expected = self.instructions[instruction_id]

        assert response["data"]["argument"] == expected["argument"]
        assert response["data"]["tags"] == expected["tags"]

    @precondition(lambda self: bool(self.sessions))
    @rule()
    def instruction_scan(self):
        session_id = next(iter(self.sessions))

        response = self.client.instruction_scan(session_id)

        assert response["http_status"] == HTTPStatus.OK

        expected_count = sum(
            1
            for item in self.instructions.values()
            if item["session"] == session_id
        )

        assert int(response["data"]["count"]) == expected_count

    @precondition(lambda self: bool(self.completions))
    @rule()
    def completion_single(self):
        completion_id = next(iter(self.completions))

        response = self.client.completion_single(completion_id)

        assert response["http_status"] == HTTPStatus.OK

        assert (
            int(response["data"]["instruction"])
            == self.completions[completion_id]
        )

        assert response["data"]["stage"] in (
            "pending",
            "running",
            "completed",
            "failed",
        )

    @precondition(lambda self: bool(self.instructions))
    @rule()
    def completion_scan(self):
        instruction_id = next(iter(self.instructions))

        response = self.client.completion_scan(instruction_id)

        assert response["http_status"] == HTTPStatus.OK

        expected_count = sum(
            1 for value in self.completions.values() if value == instruction_id
        )

        assert int(response["data"]["count"]) == expected_count

    @rule()
    def report_scan(self):
        response = self.client.report_scan()

        assert response["http_status"] == HTTPStatus.OK
        assert response["status"] == "success"

    @rule(invalid_id=st.sampled_from(["abc", "0", "-1", "invalid"]))
    def invalid_session_id(self, invalid_id):
        response = self.client.session_single(invalid_id)

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_session(self):
        response = self.client.session_single(999999999)

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @rule(invalid_id=st.sampled_from(["abc", "0", "-1", "invalid"]))
    def invalid_instruction_id(self, invalid_id):
        response = self.client.instruction_single(invalid_id)

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_instruction(self):
        response = self.client.instruction_single(999999999)

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @rule(invalid_id=st.sampled_from(["abc", "0", "-1", "invalid"]))
    def invalid_completion_id(self, invalid_id):
        response = self.client.completion_single(invalid_id)

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_completion(self):
        response = self.client.completion_single(999999999)

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @rule()
    def instruction_add_invalid_session(self):
        response = self.client.instruction_add(
            "invalid",
            "examples/red_square.gif",
            "test",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def instruction_add_missing_session(self):
        response = self.client.instruction_add(
            999999999,
            "examples/red_square.gif",
            "test",
        )

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @precondition(lambda self: bool(self.sessions))
    @rule()
    def instruction_add_empty_argument(self):
        session_id = next(iter(self.sessions))

        response = self.client.instruction_add(
            session_id,
            "",
            "test",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def invalid_session_edit_id(self):
        response = self.client.session_edit(
            "invalid",
            locale="en",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_session_edit(self):
        response = self.client.session_edit(
            999999999,
            locale="en",
        )

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @precondition(lambda self: bool(self.sessions))
    @rule()
    def invalid_session_edit_fields(self):
        session_id = next(iter(self.sessions))

        response = self.client.session_edit(
            session_id,
            unknown_field="value",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def invalid_instruction_edit_id(self):
        response = self.client.instruction_edit(
            "invalid",
            tags="test",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_instruction_edit(self):
        response = self.client.instruction_edit(
            999999999,
            tags="test",
        )

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @precondition(lambda self: bool(self.instructions))
    @rule()
    def invalid_instruction_edit_fields(self):
        instruction_id = next(iter(self.instructions))

        response = self.client.instruction_edit(
            instruction_id,
            unknown_field="value",
        )

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def invalid_instruction_scan(self):
        response = self.client.instruction_scan("invalid")

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_instruction_scan_session(self):
        response = self.client.instruction_scan(999999999)

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @rule()
    def invalid_completion_scan(self):
        response = self.client.completion_scan("invalid")

        assert response["http_status"] == HTTPStatus.BAD_REQUEST

    @rule()
    def missing_completion_scan_instruction(self):
        response = self.client.completion_scan(999999999)

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @rule(method=st.sampled_from(["GET", "POST", "PATCH"]))
    def unknown_endpoint(self, method):
        response = self.client._request(
            method,
            "/api/unknown-endpoint",
        )

        assert response["http_status"] == HTTPStatus.NOT_FOUND

    @invariant()
    def sessions_are_consistent(self):
        response = self.client.session_scan()

        assert response["http_status"] == HTTPStatus.OK
        assert int(response["data"]["count"]) == len(self.sessions)

    def teardown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


TestAPIStateMachine = APIStateMachine.TestCase

TestAPIStateMachine.settings = settings(
    max_examples=15,
    stateful_step_count=20,
    deadline=None,
)
