from floating_link_dock.geometry import Point, Rect, snap_to_edge, half_hidden_origin
from floating_link_dock.models import AppSettings
from floating_link_dock.storage import JsonStore, StoragePaths
from test_app_smoke import FakeStore, FakeStartupManager
from floating_link_dock.window import build_app


def test_existing_profile_expands_on_every_launch():
    import time
    store = FakeStore(settings=AppSettings(onboarding_complete=True))
    for _ in range(2):
        app = build_app(store, FakeStartupManager())
        try:
            deadline = time.monotonic() + .3
            while time.monotonic() < deadline:
                app.update()
                time.sleep(.01)
            assert app.is_expanded
            assert app.winfo_viewable()
        finally:
            app.destroy()


def test_snap_and_hide_on_negative_monitor():
    area = Rect(-1920, 0, 0, 1040)
    size = (78, 78)
    left = snap_to_edge(Point(-1900, 200), size, area)
    assert left == Point(-1920, 200)
    assert half_hidden_origin(left, size, area) == Point(-1959, 200)
    right = snap_to_edge(Point(-90, 200), size, area)
    assert right == Point(-78, 200)
    assert half_hidden_origin(right, size, area) == Point(-39, 200)
    middle = Point(-1000, 200)
    assert snap_to_edge(middle, size, area) == middle
    assert half_hidden_origin(middle, size, area) == middle


def test_top_bottom_snap_and_half_hide():
    area = Rect(0, 0, 1920, 1040)
    assert half_hidden_origin(snap_to_edge(Point(500, 12), (52, 52), area),
                              (52, 52), area) == Point(500, -26)
    assert half_hidden_origin(snap_to_edge(Point(500, 980), (52, 52), area),
                              (52, 52), area) == Point(500, 1014)


def test_new_settings_persist_and_old_settings_keep_defaults(tmp_path):
    store = JsonStore(StoragePaths.for_user(tmp_path))
    store.save_settings(AppSettings(edge_auto_hide=True, onboarding_complete=True))
    assert store.load_settings().value.edge_auto_hide is True
    store.paths.settings_file.write_text(
        '{"version":1,"settings":{"first_run_complete":true}}', encoding="utf-8")
    settings = store.load_settings().value
    assert settings.edge_auto_hide is False
    assert settings.onboarding_complete is False


def test_first_upgrade_expands_and_remembers_onboarding():
    store = FakeStore(settings=AppSettings(first_run_complete=True))
    app = build_app(store, FakeStartupManager())
    try:
        app._onboard()
        app.update_idletasks()
        assert app.is_expanded
        assert app.winfo_viewable()
        assert store.settings.onboarding_complete
    finally:
        app.destroy()


def test_tray_commands_are_executed_on_ui_thread():
    app = build_app(FakeStore(settings=AppSettings(onboarding_complete=True)),
                    FakeStartupManager())
    try:
        app._commands.put("show")
        app._desktop_tick()
        assert app.is_expanded
        app._commands.put("reset")
        app._desktop_tick()
        assert app.is_expanded
        assert app.snapshot.settings.x == app._collapsed_origin.x
    finally:
        app.destroy()


import pytest


@pytest.mark.parametrize('platform_name', ['win32', 'darwin'])
def test_error_is_logged_and_shown(monkeypatch, tmp_path, platform_name):
    import sys
    from pathlib import Path
    from floating_link_dock import errors
    from tkinter import messagebox
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(sys, 'platform', platform_name)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path / 'fake-home'))
    temporary_paths = StoragePaths.for_user(tmp_path)
    monkeypatch.setattr(errors.StoragePaths, 'for_user', classmethod(lambda cls: temporary_paths))
    shown = []
    monkeypatch.setattr(messagebox, "showerror", lambda *args, **kwargs: shown.append(args))
    errors.report_error(OSError("diagnostic disk failure"), parent=object())
    assert "diagnostic disk failure" in shown[0][1]
    assert "diagnostic disk failure" in (tmp_path / "FloatingLinkDock" / "errors.log").read_text(encoding="utf-8")


def test_half_hide_restores_on_hover_without_persisting_hidden_position(monkeypatch):
    import time
    from types import SimpleNamespace
    from floating_link_dock.window import FloatingDockWindow
    origin = Point(0, 200)
    current = [origin]
    settings = AppSettings(x=0, y=200, edge_auto_hide=True)
    app = SimpleNamespace(
        is_expanded=False, _drag_start=None, _hidden=False,
        _outside_since=time.monotonic() - 1, _collapsed_origin=origin,
        snapshot=SimpleNamespace(settings=settings),
        winfo_pointerxy=lambda: (500, 500),
        winfo_x=lambda: current[0].x, winfo_y=lambda: current[0].y,
        winfo_width=lambda: 52, winfo_height=lambda: 52,
        _work_area=lambda point: Rect(0, 0, 1920, 1040),
        _position=lambda point: current.__setitem__(0, point),
    )
    app._reveal = lambda: FloatingDockWindow._reveal(app)
    FloatingDockWindow._check_edge_hide(app)
    assert app._hidden
    assert current[0] == Point(-26, 200)
    assert settings.x == 0
    app.winfo_pointerxy = lambda: (5, 210)
    FloatingDockWindow._check_edge_hide(app)
    assert not app._hidden
    assert current[0] == origin
