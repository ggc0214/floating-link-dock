"""Run one real Tk window to verify physical half-hide and hover recovery."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from floating_link_dock.window import build_app
from floating_link_dock.storage import JsonStore, StoragePaths
from floating_link_dock.models import AppSettings
from floating_link_dock.geometry import Point
from floating_link_dock.windows_integration import StartupManager

root = Path(__file__).resolve().parents[1]
store = JsonStore(StoragePaths.for_user(root / ".exe-test-data" / f"edge-{time.time_ns()}"))
store.save_settings(AppSettings(onboarding_complete=True, edge_auto_hide=True))
app = build_app(store, StartupManager(root / "run.bat"))
result = {}


def verify():
    try:
        area = app._work_area()
        app._collapsed_origin = Point(area.left, area.top + 200)
        app._position(app._collapsed_origin)
        app.update_idletasks()
        width = app.winfo_width()
        app.winfo_pointerxy = lambda: (area.right - 200, area.bottom - 200)
        app._outside_since = time.monotonic() - 1
        app._check_edge_hide()
        app.update_idletasks()
        assert app._hidden
        assert app.winfo_x() == area.left - width // 2, app.winfo_x()
        app.winfo_pointerxy = lambda: (area.left + 5, area.top + 210)
        app._check_edge_hide()
        app.update_idletasks()
        assert not app._hidden
        assert app.winfo_x() == area.left
        result.update(half_hidden=True, hover_restored=True, button_width=width)
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        app.destroy()


app.after(1200, verify)
app.mainloop()
print(json.dumps(result))
raise SystemExit(1 if "error" in result else 0)
