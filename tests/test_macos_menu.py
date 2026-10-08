from queue import SimpleQueue
from types import SimpleNamespace
import sys
import pytest

from floating_link_dock import tray


def test_menu_commands_and_idempotent_lifecycle(monkeypatch):
    calls = []
    class Icon:
        def __init__(self, *args):
            self.menu = args[3]
        def run_detached(self, **kwargs):
            calls.append('start')
        def stop(self):
            calls.append('stop')
    monkeypatch.setattr(tray.pystray, 'Icon', Icon)
    monkeypatch.setattr(tray, '_set_macos_accessory_policy', lambda: None)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    commands = SimpleQueue()
    icon = tray.TrayIcon(commands)
    icon.start(); icon.start()
    for item in icon.icon.menu:
        item(icon.icon)
    assert [commands.get_nowait() for _ in range(3)] == ['show', 'reset', 'quit']
    icon.stop(); icon.stop()
    assert calls == ['start', 'stop']


@pytest.mark.skipif(sys.platform != 'darwin', reason='native Cocoa/Tk acceptance')
def test_native_tk_menu_keeps_accessory_policy_through_twenty_cycles(tmp_path):
    # Cocoa/Tk own a process-global application/autorelease pool. Test the real
    # one-app process lifecycle, independently of earlier short-lived Tk roots.
    import subprocess
    from pathlib import Path
    subprocess.run([sys.executable, '-c',
        'import runpy,sys; from pathlib import Path; '
        'sys.path.insert(0,str(Path(sys.argv[1]).parents[1]/"src")); '
        'runpy.run_path(sys.argv[1])["_native_menu_acceptance"](Path(sys.argv[2]))',
        str(Path(__file__).resolve()), str(tmp_path)], check=True, timeout=30)


def _native_menu_acceptance(tmp_path):
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
    from floating_link_dock.window import build_app
    from floating_link_dock.storage import JsonStore, StoragePaths
    from floating_link_dock.macos_lifecycle import StartupManager
    app = build_app(JsonStore(StoragePaths.for_user(tmp_path / 'data')),
                    StartupManager(tmp_path / 'Test.app', agents_dir=tmp_path / 'agents'))
    try:
        app.start_desktop_services()
        native = NSApplication.sharedApplication()
        assert native.activationPolicy() == NSApplicationActivationPolicyAccessory
        icon = app._tray.icon
        assert icon.visible
        assert icon._status_item.menu().numberOfItems() == 3
        for _ in range(20):
            app.show_panel()
            app.toggle_expanded()
            app._commands.put('show')
            app._commands.put('reset')
            app._desktop_tick()
            app.update()
            assert app.is_expanded
            assert app._tray.icon is icon
            assert native.activationPolicy() == NSApplicationActivationPolicyAccessory
        app._commands.put('quit')
        app._desktop_tick()
        assert not icon.visible
    finally:
        if app._tray is not None:
            app.destroy()
