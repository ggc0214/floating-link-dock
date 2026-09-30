from __future__ import annotations

import sys
from pathlib import Path

from .storage import JsonStore
from .window import build_app
from .windows_integration import (
    IntegrationError,
    SingleInstance,
    StartupManager,
    activate_existing_window,
    enable_dpi_awareness,
)


def _startup_target() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(__file__).resolve()


def main() -> int:
    enable_dpi_awareness()
    try:
        guard = SingleInstance()
        if not guard.acquire(activate_existing_window):
            return 0
        app = build_app(JsonStore(), StartupManager(_startup_target()))
    except (IntegrationError, OSError) as exc:
        print(f"Floating Link Dock 启动失败：{exc}", file=sys.stderr)
        return 1

    try:
        app.mainloop()
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
