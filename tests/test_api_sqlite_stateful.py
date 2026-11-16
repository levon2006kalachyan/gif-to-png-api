import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from hypothesis import settings

from src.api.client import APIClient
from src.api.server import APIHandler
from src.api.sqlite_storage import SQLiteStorage
from src.api.worker import ConversionWorker
from tests.test_api_stateful import APIStateMachine


class SQLiteAPIStateMachine(APIStateMachine):
    """Stateful-тестирование HTTP API с SQLite."""

    def __init__(self):
        super().__init__()

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test.db"
        self.storage = SQLiteStorage(db_path)

        self._start_sqlite_server()

    def _start_sqlite_server(self):
        class SQLiteTestHandler(APIHandler):
            pass

        SQLiteTestHandler.username = "test"
        SQLiteTestHandler.password = "test123"
        SQLiteTestHandler.storage = self.storage
        SQLiteTestHandler.worker = ConversionWorker(
            self.storage,
            test_mode=True,
        )

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            SQLiteTestHandler,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()

        host, port = self.server.server_address
        self.client = APIClient(
            base_url=f"http://{host}:{port}",
            username="test",
            password="test123",
        )

    def teardown(self):
        try:
            super().teardown()
        finally:
            self.storage.close()
            self.temp_dir.cleanup()


TestSQLiteAPIStateMachine = SQLiteAPIStateMachine.TestCase

TestSQLiteAPIStateMachine.settings = settings(
    max_examples=15,
    stateful_step_count=20,
    deadline=None,
)
