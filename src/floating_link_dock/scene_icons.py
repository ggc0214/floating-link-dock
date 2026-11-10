"""One font-free scene identity for small tray, floating window and EXE."""
from PIL import Image, ImageDraw

SCENE_ACCENT = '#79AFE8'
SCENE_HOVER = '#639BD8'
SCENE_BORDER = '#315D88'


def build_scene_icon(size=128):
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, 488, 488), radius=116,
                           fill=SCENE_ACCENT, outline=SCENE_BORDER, width=14)
    for x in (126, 274):
        for y in (126, 274):
            draw.rounded_rectangle((x, y, x + 112, y + 112), radius=24, fill='#F8FCFF')
    return image.resize((size, size), Image.Resampling.LANCZOS)
