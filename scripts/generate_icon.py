from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "app.ico"


def build_icon(size: int = 1024) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = size * 0.08
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=size * 0.24,
        fill="#151A1F",
        outline="#36434D",
        width=max(2, int(size * 0.018)),
    )
    draw.rounded_rectangle(
        (size * 0.19, size * 0.19, size * 0.81, size * 0.81),
        radius=size * 0.19,
        fill="#61D6C6",
    )

    stroke = max(8, int(size * 0.07))
    link_color = "#151A1F"
    first = Image.new("RGBA", image.size, (0, 0, 0, 0))
    first_draw = ImageDraw.Draw(first)
    first_draw.rounded_rectangle(
        (size * 0.27, size * 0.39, size * 0.58, size * 0.59),
        radius=size * 0.10,
        outline=link_color,
        width=stroke,
    )
    first = first.rotate(-38, resample=Image.Resampling.BICUBIC, center=(size / 2, size / 2))
    image.alpha_composite(first)

    second = Image.new("RGBA", image.size, (0, 0, 0, 0))
    second_draw = ImageDraw.Draw(second)
    second_draw.rounded_rectangle(
        (size * 0.42, size * 0.41, size * 0.73, size * 0.61),
        radius=size * 0.10,
        outline=link_color,
        width=stroke,
    )
    second = second.rotate(-38, resample=Image.Resampling.BICUBIC, center=(size / 2, size / 2))
    image.alpha_composite(second)
    return image


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.save(
        OUTPUT,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
