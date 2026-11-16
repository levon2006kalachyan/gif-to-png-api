from pathlib import Path

import pytest
from PIL import Image

from src.converter import convert_gif_to_png


@pytest.mark.parametrize(
    "filename",
    [
        "red_square.gif",
        "blue_circle.gif",
        "green_triangle.gif",
        "yellow_rectangle.gif",
    ],
)
def test_convert_four_examples(filename, tmp_path):
    """Проверка преобразования четырёх GIF-файлов."""

    input_path = Path("examples") / filename
    output_path = tmp_path / filename.replace(".gif", ".png")

    result = convert_gif_to_png(
        str(input_path),
        str(output_path),
    )

    assert output_path.exists()
    assert Path(result) == output_path

    with Image.open(input_path) as source, Image.open(output_path) as output:
        assert output.format == "PNG"
        assert output.size == source.size


def test_missing_file(tmp_path):
    """Проверка отсутствующего входного файла."""

    with pytest.raises(FileNotFoundError):
        convert_gif_to_png(
            "nonexistent.gif",
            str(tmp_path / "result.png"),
        )


def test_invalid_extension(tmp_path):
    """Проверка неправильного расширения."""

    input_path = tmp_path / "image.txt"
    input_path.write_text("not a gif")

    with pytest.raises(ValueError):
        convert_gif_to_png(
            str(input_path),
            str(tmp_path / "result.png"),
        )


def test_invalid_gif_content(tmp_path):
    """Проверка повреждённого GIF."""

    input_path = tmp_path / "broken.gif"
    input_path.write_bytes(b"invalid gif content")

    with pytest.raises(ValueError):
        convert_gif_to_png(
            str(input_path),
            str(tmp_path / "result.png"),
        )


def test_output_directory_created(tmp_path):
    """Проверка автоматического создания папки."""

    input_path = Path("examples/red_square.gif")
    output_path = tmp_path / "nested" / "result.png"

    convert_gif_to_png(
        str(input_path),
        str(output_path),
    )

    assert output_path.exists()
