
from pathlib import Path

from PIL import Image, ImageDraw


EXAMPLES_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def create_gif(filename, size, color, shape):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)

    width, height = size

    if shape == "rectangle":
        draw.rectangle(
            (20, 20, width - 20, height - 20),
            fill=color
        )

    elif shape == "ellipse":
        draw.ellipse(
            (20, 20, width - 20, height - 20),
            fill=color
        )

    elif shape == "triangle":
        draw.polygon(
            [
                (width // 2, 10),
                (10, height - 10),
                (width - 10, height - 10)
            ],
            fill=color
        )

    image.save(EXAMPLES_DIR / filename, format="GIF")
    print(f"Создан файл: {filename}")


create_gif("red_square.gif", (200, 200), "red", "rectangle")
create_gif("blue_circle.gif", (300, 300), "blue", "ellipse")
create_gif("green_triangle.gif", (250, 250), "green", "triangle")
create_gif("yellow_rectangle.gif", (400, 200), "yellow", "rectangle")
