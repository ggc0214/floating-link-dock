import ctypes
import sys
from ctypes import wintypes

import pytest

from floating_link_dock.window import build_app
from test_app_smoke import FakeStore, FakeStartupManager


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows taskbar styles')
def test_dock_remains_tool_window_when_expanded_collapsed_and_restored():
    app = build_app(FakeStore([]), FakeStartupManager())
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    try:
        for action in (lambda: None, app.show_panel, app.toggle_expanded,
                       app.show_panel, app.withdraw, app.show_panel):
            action()
            app.update()
            hwnd = user32.GetAncestor(app.winfo_id(), 2)
            assert hwnd
            style = user32.GetWindowLongW(hwnd, -20)
            assert style & 0x80, 'Dock must use WS_EX_TOOLWINDOW to stay out of taskbar'
            assert not style & 0x40000, 'WS_EX_APPWINDOW must not force a taskbar button'
    finally:
        app.destroy()
