import base64
import binascii
import hmac


def check_basic_auth(
    authorization_header: str | None,
    username: str,
    password: str,
) -> bool:
    """Проверяет HTTP Basic Authentication (RFC 7617)."""

    if not authorization_header:
        return False

    try:
        scheme, encoded_credentials = authorization_header.split(" ", 1)

        if scheme.lower() != "basic":
            return False

        decoded = base64.b64decode(
            encoded_credentials,
            validate=True,
        ).decode("utf-8")

        received_username, received_password = decoded.split(":", 1)

        return hmac.compare_digest(
            received_username, username
        ) and hmac.compare_digest(received_password, password)

    except (
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
    ):
        return False
