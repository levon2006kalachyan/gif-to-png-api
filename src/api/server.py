import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

from src.api.auth import check_basic_auth
from src.api.sqlite_storage import SQLiteStorage
from src.api.storage import MemoryStorage
from src.api.worker import ConversionWorker
from src.api.xml_utils import create_xml_response

MAX_XML_BODY_SIZE = 1024 * 1024


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API для асинхронного преобразования GIF в PNG."""

    username = "admin"
    password = "admin123"
    storage = MemoryStorage()
    worker = None

    def send_xml(self, status_code, status, message, data=None):
        body = create_xml_response(status, message, data)

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/xml; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticate(self):
        authorization = self.headers.get("Authorization")

        if check_basic_auth(
            authorization,
            self.username,
            self.password,
        ):
            return True

        body = create_xml_response("error", "Unauthorized")

        self.send_response(401)
        self.send_header(
            "WWW-Authenticate",
            'Basic realm="GIF to PNG API", charset="UTF-8"',
        )
        self.send_header(
            "Content-Type",
            "application/xml; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        return False

    def get_query(self):
        parsed = urlparse(self.path)

        return {
            key: values[0]
            for key, values in parse_qs(
                parsed.query,
                keep_blank_values=True,
            ).items()
        }

    def get_xml_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error

        if length <= 0 or length > MAX_XML_BODY_SIZE:
            raise ValueError("Invalid XML body length")

        body = self.rfile.read(length)

        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as error:
            raise ValueError("Invalid XML body") from error

        return {child.tag: child.text or "" for child in root}

    @staticmethod
    def parse_id(value):
        try:
            identifier = int(value)

            if identifier <= 0:
                raise ValueError

            return identifier
        except (TypeError, ValueError):
            return None

    def do_GET(self):
        if not self.authenticate():
            return

        path = urlparse(self.path).path
        routes = {
            "/api/health": self.get_health,
            "/api/session-scan": self.get_session_scan,
            "/api/session-single": self.get_session_single,
            "/api/instruction-single": self.get_instruction_single,
            "/api/completion-single": self.get_completion_single,
            "/api/report-scan": self.get_report_scan,
        }

        handler = routes.get(path)
        if handler is not None:
            handler()
        elif path.startswith("/api/instruction-scan/"):
            self.get_instruction_scan(path)
        elif path.startswith("/api/completion-scan/"):
            self.get_completion_scan(path)
        else:
            self.send_xml(404, "error", "Endpoint not found")

    def get_health(self):
        self.send_xml(
            200,
            "success",
            "Server is running",
            {"service": "gif-to-png-api"},
        )

    def get_session_scan(self):
        sessions = self.storage.scan_sessions()
        data = {"count": len(sessions)}

        for index, session in enumerate(sessions):
            data[f"session_{index}_id"] = session["id"]
            data[f"session_{index}_locale"] = session["locale"]

        self.send_xml(200, "success", "Sessions found", data)

    def get_session_single(self):
        session_id = self.parse_id(self.get_query().get("id"))

        if session_id is None:
            self.send_xml(400, "error", "Invalid session id")
            return

        session = self.storage.get_session(session_id)
        if session is None:
            self.send_xml(404, "error", "Session not found")
            return

        self.send_xml(200, "success", "Session found", session)

    def get_instruction_scan(self, path):
        session_id = self.parse_id(path.rsplit("/", 1)[-1])

        if session_id is None:
            self.send_xml(400, "error", "Invalid session id")
            return

        if self.storage.get_session(session_id) is None:
            self.send_xml(404, "error", "Session not found")
            return

        instructions = self.storage.scan_instructions(session_id)
        data = {"count": len(instructions)}

        for index, instruction in enumerate(instructions):
            prefix = f"instruction_{index}"
            data[f"{prefix}_id"] = instruction["id"]
            data[f"{prefix}_argument"] = instruction["argument"]
            data[f"{prefix}_tags"] = instruction["tags"]

        self.send_xml(200, "success", "Instructions found", data)

    def get_instruction_single(self):
        instruction_id = self.parse_id(self.get_query().get("id"))

        if instruction_id is None:
            self.send_xml(400, "error", "Invalid instruction id")
            return

        instruction = self.storage.get_instruction(instruction_id)
        if instruction is None:
            self.send_xml(404, "error", "Instruction not found")
            return

        self.send_xml(200, "success", "Instruction found", instruction)

    def get_completion_scan(self, path):
        instruction_id = self.parse_id(path.rsplit("/", 1)[-1])

        if instruction_id is None:
            self.send_xml(400, "error", "Invalid instruction id")
            return

        if self.storage.get_instruction(instruction_id) is None:
            self.send_xml(404, "error", "Instruction not found")
            return

        completions = self.storage.scan_completions(instruction_id)
        data = {"count": len(completions)}

        for index, completion in enumerate(completions):
            prefix = f"completion_{index}"
            for key, value in completion.items():
                data[f"{prefix}_{key}"] = value

        self.send_xml(200, "success", "Completions found", data)

    def get_completion_single(self):
        completion_id = self.parse_id(self.get_query().get("id"))

        if completion_id is None:
            self.send_xml(400, "error", "Invalid completion id")
            return

        completion = self.storage.get_completion(completion_id)
        if completion is None:
            self.send_xml(404, "error", "Completion not found")
            return

        self.send_xml(200, "success", "Completion found", completion)

    def get_report_scan(self):
        report = self.storage.report_scan()
        data = {"count": len(report)}

        for index, row in enumerate(report):
            prefix = f"report_{index}"
            for key, value in row.items():
                data[f"{prefix}_{key}"] = value

        self.send_xml(200, "success", "Report generated", data)

    def do_POST(self):
        if not self.authenticate():
            return

        path = urlparse(self.path).path
        query = self.get_query()

        if path == "/api/session-add":
            self.post_session_add(query)
        elif path == "/api/instruction-add":
            self.post_instruction_add(query)
        else:
            self.send_xml(404, "error", "Endpoint not found")

    def post_session_add(self, query):
        session = self.storage.add_session(
            locale=query.get("locale", ""),
            user_agent=query.get("user_agent", ""),
        )
        self.send_xml(200, "success", "Session created", session)

    def post_instruction_add(self, query):
        session_id = self.parse_id(query.get("session"))
        argument = query.get("argument", "")
        tags = query.get("tags", "")

        if session_id is None:
            self.send_xml(400, "error", "Invalid session id")
            return

        if not argument:
            self.send_xml(400, "error", "Argument is required")
            return

        try:
            instruction = self.storage.add_instruction(
                session_id=session_id,
                argument=argument,
                tags=tags,
            )
        except ValueError as error:
            self.send_xml(404, "error", str(error))
            return

        if self.worker is None:
            self.send_xml(503, "error", "Worker unavailable")
            return

        completion = self.worker.start(instruction)
        response_data = dict(instruction)
        response_data["completion_id"] = completion["id"]
        response_data["stage"] = completion["stage"]

        self.send_xml(200, "success", "Instruction created", response_data)

    def do_PATCH(self):
        if not self.authenticate():
            return

        path = urlparse(self.path).path

        if path.startswith("/api/session-edit/"):
            self.patch_session(path)
        elif path.startswith("/api/instruction-edit/"):
            self.patch_instruction(path)
        else:
            self.send_xml(404, "error", "Endpoint not found")

    def patch_session(self, path):
        session_id = self.parse_id(path.rsplit("/", 1)[-1])

        if session_id is None:
            self.send_xml(400, "error", "Invalid session id")
            return

        try:
            changes = self.get_xml_body()
        except ValueError as error:
            self.send_xml(400, "error", str(error))
            return

        allowed = {"locale", "user_agent"}
        if not changes or not set(changes).issubset(allowed):
            self.send_xml(400, "error", "Invalid session fields")
            return

        session = self.storage.edit_session(session_id, **changes)

        if session is None:
            self.send_xml(404, "error", "Session not found")
            return

        self.send_xml(200, "success", "Session updated", session)

    def patch_instruction(self, path):
        instruction_id = self.parse_id(path.rsplit("/", 1)[-1])

        if instruction_id is None:
            self.send_xml(400, "error", "Invalid instruction id")
            return

        try:
            changes = self.get_xml_body()
        except ValueError as error:
            self.send_xml(400, "error", str(error))
            return

        allowed = {"argument", "tags"}
        if not changes or not set(changes).issubset(allowed):
            self.send_xml(400, "error", "Invalid instruction fields")
            return

        instruction = self.storage.edit_instruction(instruction_id, **changes)

        if instruction is None:
            self.send_xml(404, "error", "Instruction not found")
            return

        self.send_xml(200, "success", "Instruction updated", instruction)


def parse_arguments():
    parser = argparse.ArgumentParser(description="GIF to PNG HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Do not execute real GIF conversions",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    APIHandler.username = args.username
    APIHandler.password = args.password
    APIHandler.storage = SQLiteStorage("gif_to_png.db")
    APIHandler.worker = ConversionWorker(
        APIHandler.storage,
        test_mode=args.test_mode,
    )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        APIHandler,
    )

    print(
        "GIF to PNG API started: http://{}:{}".format(args.host, args.port),
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n????????? ???????...")
    finally:
        server.server_close()
        APIHandler.storage.close()


if __name__ == "__main__":
    main()
