"""Check real tile mouse events and persisted coordinates without opening websites."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from floating_link_dock.window import build_app
from floating_link_dock.storage import JsonStore, StoragePaths
from floating_link_dock.windows_integration import StartupManager

root = Path(__file__).resolve().parents[1]
store = JsonStore(StoragePaths.for_user(root / ".exe-test-data" / f"tiles-{time.time_ns()}"))
app = build_app(store, StartupManager(root / "run.bat"))
opened = []
app._open_link = lambda link: opened.append(link.id)
result = {}


def verify():
    try:
        app.show_panel()
        app.update_idletasks()
        board = app.board
        key = app.snapshot.links[0].id
        tile = board._items[key][1]
        start = board.canvas.coords(board._items[key][0])
        tile._canvas.event_generate("<ButtonPress-1>", x=10, y=10)
        tile._canvas.event_generate("<B1-Motion>", x=80, y=100)
        app.update_idletasks()
        tile._canvas.event_generate("<ButtonRelease-1>", x=10, y=10)
        assert not opened, "Dragging opened a website"
        saved = next(link for link in store.load_links().value if link.id == key)
        assert saved.x > 8 and saved.y > 8, saved
        app._render_expanded()
        app.update_idletasks()
        board = app.board
        tile = board._items[key][1]
        restored = board.canvas.coords(board._items[key][0])
        assert abs(restored[0] - saved.x * board._scale) <= 1
        assert abs(restored[1] - saved.y * board._scale) <= 1
        tile._canvas.event_generate("<ButtonPress-1>", x=10, y=10)
        tile._canvas.event_generate("<ButtonRelease-1>", x=10, y=10)
        assert opened == [key], opened
        tile._canvas.event_generate("<ButtonPress-1>", x=10, y=10)
        tile._canvas.event_generate("<B1-Motion>", x=10000, y=10000)
        app.update_idletasks()
        tile._canvas.event_generate("<ButtonRelease-1>", x=10, y=10)
        x, y = board.canvas.coords(board._items[key][0])
        assert x + 96 * board._scale <= board.canvas.winfo_width() + 1
        assert y + 96 * board._scale <= board._content_height + 1
        result.update(drag_without_open=True, click_opens=True,
                      restored_position=[saved.x, saved.y], constrained_to_board=True)
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        app.destroy()


app.after(500, verify)
app.mainloop()
print(json.dumps(result))
raise SystemExit(1 if "error" in result else 0)
