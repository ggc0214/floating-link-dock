"""Font-independent, supersampled face for the desktop button."""
from PIL import Image, ImageDraw

from . import theme


def build_face_icon() -> Image.Image:
    image = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 118, 118), fill=theme.SURFACE,
                 outline=theme.TEXT, width=6)
    draw.ellipse((39, 45, 49, 59), fill=theme.TEXT)
    draw.ellipse((79, 45, 89, 59), fill=theme.TEXT)
    draw.arc((36, 50, 92, 91), 15, 165, fill=theme.TEXT, width=6)
    return image
