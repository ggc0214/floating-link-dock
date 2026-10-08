from pathlib import Path
from types import SimpleNamespace
import sys

from floating_link_dock import main, window


def test_frozen_startup_target_is_app_bundle(monkeypatch, tmp_path):
    executable = tmp_path / 'Apps With Spaces/FloatingLinkDock.app/Contents/MacOS/FloatingLinkDock'
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    assert main._startup_target() == executable.parents[2]


def test_finder_reopen_is_queued():
    from queue import SimpleQueue
    app = SimpleNamespace(_commands=SimpleQueue())
    window.FloatingDockWindow._mac_reopen(app)
    assert app._commands.get_nowait() == 'show'


def test_windows_frozen_build_keeps_dynamic_backend():
    source = Path('FloatingLinkDock.spec').read_text(encoding='utf-8')
    assert 'floating_link_dock.windows_integration' in source
