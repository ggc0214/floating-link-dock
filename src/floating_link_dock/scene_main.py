"""Windows-only scene entry; keeps legacy app/data/startup identifiers intact."""
from pathlib import Path
import sys
from .scene_store import SceneStore

TITLE = 'Floating Link Dock Scenes'
APP_ID = 'FloatingLinkDockScenes'


def report_scene_error(exc, parent=None, *, root=None):
    from .errors import report_error
    report_error(exc, parent=parent, root=root if root is not None else SceneStore().root)


def main():
    if sys.platform != 'win32':
        print('场景版第一版仅支持 Windows；Mac 请继续使用原版源码。', file=sys.stderr)
        return 2
    from .windows_integration import SingleInstance, StartupManager, activate_existing_window, enable_dpi_awareness
    from .scene_window import build_scenes_app
    from tkinter import Tk, messagebox
    guard = None; app = None; prompt = None
    enable_dpi_awareness()
    try:
        guard = SingleInstance(name='Local\\' + APP_ID)
        if not guard.acquire(lambda: activate_existing_window(TITLE)): return 0
        store = SceneStore()
        if store.needs_initialization():
            import_old = False
            if (store.legacy_root / 'links.json').exists():
                prompt = Tk(); prompt.withdraw()
                import_old = messagebox.askyesno('导入原网址', '是否把原版的网址和布局复制到“常用网址”场景？\n原版文件保持不变。', parent=prompt)
                prompt.destroy(); prompt = None
            store.initialize(import_old)
        target = Path(sys.executable) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2] / 'launcher_scenes.py'
        app = build_scenes_app(store, StartupManager(target, value_name=APP_ID))
        app.start_desktop_services(); app.mainloop()
        return 0
    except Exception as exc:
        report_scene_error(exc)
        return 1
    finally:
        if prompt is not None: prompt.destroy()
        if app is not None:
            try: app.destroy()
            except Exception: pass
        if guard is not None: guard.close()
