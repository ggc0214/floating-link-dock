import runpy
from pathlib import Path
from types import SimpleNamespace


def test_scene_spec_builds_only_scene_entry(monkeypatch):
    import PyInstaller.utils.hooks
    monkeypatch.setattr(PyInstaller.utils.hooks, 'collect_data_files', lambda name: [('public', name)])
    captured = {}
    def analysis(scripts, **kw):
        captured['scripts'] = scripts; captured['analysis'] = kw
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    def exe(*args, **kw): captured['exe'] = kw
    runpy.run_path('FloatingLinkDockScenes.spec', init_globals={'Analysis': analysis, 'PYZ': lambda *a: None, 'EXE': exe})
    assert captured['scripts'] == ['launcher_scenes.py']
    assert captured['exe']['name'] == 'FloatingLinkDockScenes'
    assert captured['exe']['icon'] == ['assets/scene.ico']
    assert 'floating_link_dock.windows_integration' in captured['analysis']['hiddenimports']
    assert captured['analysis']['datas'] == [('public', 'customtkinter')]
