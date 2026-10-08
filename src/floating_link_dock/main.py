from __future__ import annotations

import sys
from pathlib import Path

from .storage import JsonStore
from .window import build_app
from .platform_integration import (
    IntegrationError,
    SingleInstance,
    StartupManager,
    activate_existing_window,
    enable_dpi_awareness,
)


def _startup_target() -> Path:
    if sys.platform == 'darwin':
        if getattr(sys, 'frozen', False):
            executable = Path(sys.executable).resolve()
            for parent in executable.parents:
                if parent.suffix == '.app':
                    return parent
        return Path(__file__).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(__file__).resolve().parents[2] / "run.bat"


def main() -> int:
    enable_dpi_awareness()
    guard = None
    app = None
    try:
        guard = SingleInstance()
        if not guard.acquire(activate_existing_window):
            return 0
        app = build_app(JsonStore(), StartupManager(_startup_target()))
        if hasattr(guard, 'bind_commands'):
            guard.bind_commands(app._commands)
        app.start_desktop_services()
        app.mainloop()
    except Exception as exc:
        from .errors import report_error
        report_error(exc)
        return 1
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        if guard is not None:
            guard.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
