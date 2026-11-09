"""Generate only the scene app icon; original assets/app.ico stays untouched."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from floating_link_dock.scene_icons import build_scene_icon


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[1] / 'assets/scene.ico'
    build_scene_icon(512).save(output, format='ICO', sizes=[(16, 16), (24, 24), (32, 32),
                               (48, 48), (64, 64), (128, 128), (256, 256)])
    print(output)
