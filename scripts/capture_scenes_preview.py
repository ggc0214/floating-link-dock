"""Capture only our public-fixture window, never the user's saved profile."""
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PIL import ImageGrab
from floating_link_dock.scene_store import SceneStore
from floating_link_dock.scene_controller import SceneController
from floating_link_dock.scene_models import ResourceDraft
from floating_link_dock.scene_window import build_scenes_app


class DisabledStartup:
    def is_enabled(self): return False
    def set_enabled(self, enabled): raise ValueError('Preview does not change login settings')


def main():
    root = Path(__file__).resolve().parents[1]
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'docs/work-scenes/preview.png'
    with tempfile.TemporaryDirectory(prefix='scenes-preview-') as directory:
        store = SceneStore(Path(directory) / 'new', Path(directory) / 'old'); store.initialize(False)
        controller = SceneController(store); controller.initialize()
        for draft in [ResourceDraft('url', '飞书', 'https://www.feishu.cn'),
                      ResourceDraft('url', 'GitHub', 'https://github.com'),
                      ResourceDraft('url', 'ChatGPT', 'https://chatgpt.com')]:
            controller.add_resource(draft)
        if '--empty-work' not in sys.argv[2:]:
            controller.duplicate_scene('产品开发')
            first_scene = controller.snapshot.document.active_scene
            for draft in [ResourceDraft('folder', '款式资料', r'\\NAS-DEMO\共享目录\款式资料'),
                      ResourceDraft('file', '成本表', r'\\NAS-DEMO\共享目录\成本表.xlsx'),
                      ResourceDraft('url', '飞书多维表', 'https://www.feishu.cn/base/demo')]:
                controller.add_resource(draft)
            controller.create_scene('日常运营')
            controller.add_resource(ResourceDraft('url', '飞书', 'https://www.feishu.cn'))
            controller.create_scene('周报整理')
            controller.add_resource(ResourceDraft('file', '周报', r'C:\示例\周报.xlsx'))
            controller.add_resource(ResourceDraft('folder', '工作资料', r'C:\示例'))
            controller.select_scene(first_scene.id)
        app = build_scenes_app(store, DisabledStartup())
        try:
            app.show_panel(); app.lift()
            if '--common' in sys.argv[2:]: app._select_section('常用网址')
            if '--empty-work' in sys.argv[2:]: app._select_section('工作场景')
            if '--edit' in sys.argv[2:]: app._configure_scene(app.snapshot.document.active_scene)
            until = time.monotonic() + .4
            while time.monotonic() < until: app.update(); time.sleep(.01)
            if '--collapsed' in sys.argv[2:]:
                app.toggle_expanded(); app.update(); time.sleep(.1)
            box = (app.winfo_rootx(), app.winfo_rooty(),
                   app.winfo_rootx() + app.winfo_width(), app.winfo_rooty() + app.winfo_height())
            ImageGrab.grab(bbox=box).save(output)
            print(str(output))
        finally: app.destroy()


if __name__ == '__main__': main()
