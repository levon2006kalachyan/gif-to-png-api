
from xml.etree.ElementTree import Element, SubElement, tostring


def create_xml_response(
    status: str,
    message: str,
    data: dict | None = None,
) -> bytes:
    """Создаёт XML-ответ HTTP API."""

    root = Element("response")

    status_element = SubElement(root, "status")
    status_element.text = status

    message_element = SubElement(root, "message")
    message_element.text = message

    if data:
        data_element = SubElement(root, "data")

        for key, value in data.items():
            item = SubElement(data_element, str(key))
            item.text = str(value)

    return tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )
