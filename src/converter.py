
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def convert_gif_to_png(input_path: str, output_path: str) -> str:
    """Преобразует GIF-файл в PNG и сохраняет результат на диск."""

    source = Path(input_path)
    destination = Path(output_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Входной файл не найден: {source}"
        )

    if source.suffix.lower() != ".gif":
        raise ValueError("Входной файл должен иметь расширение .gif")

    if source.resolve() == destination.resolve():
        raise ValueError("Входной и выходной пути должны различаться")

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(source) as image:
            if image.format != "GIF":
                raise ValueError("Файл не является изображением GIF")

            image.seek(0)
            frame = image.convert("RGBA")
            frame.save(destination, format="PNG")

    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(
            f"Не удалось обработать GIF-файл: {source}"
        ) from error

    return str(destination)


def main() -> int:
    """Читает пути из stdin и запускает преобразование."""

    try:
        print(
            "Введите путь к GIF-файлу:",
            file=sys.stderr
        )
        input_path = sys.stdin.readline().strip().strip('"')

        if not input_path:
            raise ValueError("Не указан путь к GIF-файлу")

        print(
            "Введите путь для сохранения PNG:",
            file=sys.stderr
        )
        output_path = sys.stdin.readline().strip().strip('"')

        if not output_path:
            raise ValueError("Не указан путь для сохранения PNG")

        result = convert_gif_to_png(input_path, output_path)

        print(f"SUCCESS: {result}")
        return 0

    except (
        FileNotFoundError,
        ValueError,
        UnidentifiedImageError,
        OSError
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
