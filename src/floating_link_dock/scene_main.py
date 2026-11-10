"""Scene launcher with independent app, data and startup identifiers."""
from pathlib import Path
import sys
from .scene_store import SceneStore

TITLE = 'Floating Link Dock Scenes'
APP_ID = 'FloatingLinkDockScenes'
MAC_STARTUP_LABEL = 'cn.floatinglinkdock.scenes.launcher'


def report_scene_error(exc, parent=None, *, root=None):
    from .errors import report_error
    report_error(exc, parent=parent, root=root if root is not None else SceneStore().root)


def main():
    if sys.platform not in {'win32', 'darwin'}:
        print('工作场景版支持 Windows 和 macOS。', file=sys.stderr)
        return 2
    from .platform_integration import SingleInstance, StartupManager, activate_existing_window, enable_dpi_awareness
    from .scene_window import build_scenes_app
    from tkinter import Tk, messagebox
    guard = None; app = None; prompt = None
    enable_dpi_awareness()
    try:
        store = SceneStore()
        target = Path(sys.executable) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2] / 'launcher_scenes.py'
        if sys.platform == 'darwin':
            target = next((parent for parent in target.resolve().parents if parent.suffix == '.app'), target)
            guard = SingleInstance(root=store.root)
            wake_existing = activate_existing_window
            startup = StartupManager(target, label=MAC_STARTUP_LABEL)
        else:
            guard = SingleInstance(name='Local\\' + APP_ID)
            wake_existing = lambda: activate_existing_window(TITLE)
            startup = StartupManager(target, value_name=APP_ID)
        if not guard.acquire(wake_existing): return 0
        if store.needs_initialization():
            import_old = False
            if (store.legacy_root / 'links.json').exists():
                prompt = Tk(); prompt.withdraw()
                import_old = messagebox.askyesno('导入原网址', '是否把原版的网址和布局复制到“常用网址”场景？\n原版文件保持不变。', parent=prompt)
                prompt.destroy(); prompt = None
            store.initialize(import_old)
        app = build_scenes_app(store, startup)
        if sys.platform == 'darwin':
            guard.bind_commands(app._commands)
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
