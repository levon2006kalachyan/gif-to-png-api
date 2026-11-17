import base64
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree


class APIClient:
    """HTTP-клиент для GIF to PNG API."""

    def __init__(
        self,
        base_url="http://127.0.0.1:8765",
        username="admin",
        password="admin123",
        timeout=10,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        credentials = (username + ":" + password).encode()
        encoded = base64.b64encode(credentials).decode("ascii")

        self.authorization = f"Basic {encoded}"

    @staticmethod
    def _build_xml_body(xml_body):
        root = ElementTree.Element("request")

        for key, value in xml_body.items():
            child = ElementTree.SubElement(root, key)
            child.text = str(value)

        return ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    @staticmethod
    def _parse_response(status_code, response_body):
        try:
            root = ElementTree.fromstring(response_body)
        except ElementTree.ParseError as error:
            raise ValueError("Invalid XML response") from error

        result = {
            "http_status": status_code,
            "status": root.findtext("status", ""),
            "message": root.findtext("message", ""),
            "data": {},
        }

        data_element = root.find("data")
        if data_element is not None:
            for child in data_element:
                result["data"][child.tag] = child.text or ""

        return result

    def _send_request(self, request):
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()
        except URLError as error:
            raise ConnectionError(f"Cannot connect to API: {error}") from error

    def _request(self, method, path, params=None, xml_body=None):
        url = self.base_url + path

        if params:
            url += "?" + urlencode(params)

        headers = {
            "Authorization": self.authorization,
            "Accept": "application/xml",
        }

        body = None
        if xml_body is not None:
            body = self._build_xml_body(xml_body)
            headers["Content-Type"] = "application/xml"

        request = Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        status_code, response_body = self._send_request(request)
        return self._parse_response(status_code, response_body)

    def session_add(self, locale="", user_agent=""):
        return self._request(
            "POST",
            "/api/session-add",
            params={
                "locale": locale,
                "user_agent": user_agent,
            },
        )

    def session_scan(self):
        return self._request(
            "GET",
            "/api/session-scan",
        )

    def session_single(self, session_id):
        return self._request(
            "GET",
            "/api/session-single",
            params={"id": session_id},
        )

    def session_edit(self, session_id, **changes):
        return self._request(
            "PATCH",
            f"/api/session-edit/{session_id}",
            xml_body=changes,
        )

    def instruction_add(
        self,
        session_id,
        argument,
        tags="",
    ):
        return self._request(
            "POST",
            "/api/instruction-add",
            params={
                "session": session_id,
                "argument": argument,
                "tags": tags,
            },
        )

    def instruction_scan(self, session_id):
        return self._request(
            "GET",
            f"/api/instruction-scan/{session_id}",
        )

    def instruction_single(self, instruction_id):
        return self._request(
            "GET",
            "/api/instruction-single",
            params={"id": instruction_id},
        )

    def instruction_edit(self, instruction_id, **changes):
        return self._request(
            "PATCH",
            f"/api/instruction-edit/{instruction_id}",
            xml_body=changes,
        )

    def completion_scan(self, instruction_id):
        return self._request(
            "GET",
            f"/api/completion-scan/{instruction_id}",
        )

    def completion_single(self, completion_id):
        return self._request(
            "GET",
            "/api/completion-single",
            params={"id": completion_id},
        )

    def report_scan(self):
        return self._request(
            "GET",
            "/api/report-scan",
        )

    def health(self):
        return self._request(
            "GET",
            "/api/health",
        )
