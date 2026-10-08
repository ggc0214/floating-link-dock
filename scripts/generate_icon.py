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
        fill="#A8E4CF",
        outline="#6B9184",
        width=max(2, int(size * 0.018)),
    )
    draw.rounded_rectangle(
        (size * 0.19, size * 0.19, size * 0.81, size * 0.81),
        radius=size * 0.19,
        fill="#A8E4CF",
    )

    ink = "#344B49"
    draw.ellipse((size*.31, size*.34, size*.39, size*.44), fill=ink)
    draw.ellipse((size*.61, size*.34, size*.69, size*.44), fill=ink)
    draw.arc((size*.28, size*.38, size*.72, size*.72), 10, 170,
             fill=ink, width=max(2, int(size*.045)))
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
