import sys
from floating_link_dock import scene_main
from floating_link_dock.windows_integration import StartupManager
from test_windows_integration import MemoryRegistry
from floating_link_dock.scene_store import SceneStore


def test_startup_values_are_isolated(tmp_path):
    registry = MemoryRegistry()
    old = StartupManager(tmp_path / 'old.exe', registry)
    new = StartupManager(tmp_path / 'new.exe', registry, value_name='FloatingLinkDockScenes')
    old.set_enabled(True); new.set_enabled(True); new.set_enabled(False)
    assert old.is_enabled() and not new.is_enabled()
    assert 'FloatingLinkDock' in registry.values


def test_default_directories_are_separate(monkeypatch, tmp_path):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    store = SceneStore()
    assert store.root == tmp_path / 'FloatingLinkDockScenes'
    assert store.legacy_root == tmp_path / 'FloatingLinkDock'


def test_scenes_error_log_never_uses_old_profile(monkeypatch, tmp_path):
    from floating_link_dock import errors
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(errors, 'show_startup_error', lambda message: None)
    scene_main.report_scene_error(OSError('example failure'), root=tmp_path / 'FloatingLinkDockScenes')
    assert (tmp_path / 'FloatingLinkDockScenes/errors.log').exists()
    assert not (tmp_path / 'FloatingLinkDock').exists()


def test_unsupported_platform_refuses_before_loading_os_services(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    assert scene_main.main() == 2
