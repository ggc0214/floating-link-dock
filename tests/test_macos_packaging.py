from pathlib import Path
import plistlib
import runpy
import sys
import struct
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('minimum,expected', [(11, '13.0.0'), (26, '26.0.0')])
def test_bundle_minimum_covers_compiled_dependencies(tmp_path, minimum, expected):
    # Minimal arm64 Mach-O with a real LC_BUILD_VERSION command.
    binary = tmp_path / 'Python'
    binary.write_bytes(struct.pack('<8I6I',
        0xfeedfacf, 0x100000c, 0, 2, 1, 24, 0, 0,
        0x32, 24, 1, minimum << 16, 26 << 16, 0))
    (tmp_path / 'resource.txt').write_text('public resource')
    module = runpy.run_path(str(ROOT / 'scripts/build_macos.py'))
    assert module['minimum_system_version'](tmp_path) == expected


@pytest.mark.parametrize('scenes,name,launcher,bundle_id', [
    ('0', 'FloatingLinkDock', 'launcher.py', 'cn.floatinglinkdock.app'),
    ('1', 'FloatingLinkDockScenes', 'launcher_scenes.py', 'cn.floatinglinkdock.scenes'),
])
def test_bundle_plist_and_inputs(tmp_path, monkeypatch, scenes, name, launcher, bundle_id):
    monkeypatch.setenv('FLOATING_LINK_DOCK_BUILD_SCENES', scenes)
    (tmp_path / 'Python').write_bytes(struct.pack('<8I6I',
        0xfeedfacf, 0x100000c, 0, 2, 1, 24, 0, 0,
        0x32, 24, 1, 26 << 16, 26 << 16, 0))
    import PyInstaller.utils.hooks
    monkeypatch.setattr(PyInstaller.utils.hooks, 'collect_data_files', lambda name: [('public', name)])
    captured = {}
    def analysis(*args, **kwargs):
        captured['entry'] = args[0]
        captured['analysis'] = kwargs
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    def bundle(*args, **kwargs):
        captured['bundle'] = kwargs
        return kwargs
    runpy.run_path(str(ROOT / 'FloatingLinkDock-macos.spec'), init_globals={
        'Analysis': analysis, 'PYZ': lambda *a: None,
        'EXE': lambda *a, **kw: captured.update(exe=kw),
        'COLLECT': lambda *a, **kw: SimpleNamespace(name=str(tmp_path)), 'BUNDLE': bundle,
        'SPECPATH': str(ROOT),
    })
    final_plist = plistlib.loads(plistlib.dumps(captured['bundle']['info_plist']))
    assert final_plist['LSUIElement'] is True
    assert final_plist['LSMinimumSystemVersion'] == '26.0.0'
    assert final_plist['CFBundleIdentifier'] == bundle_id
    assert captured['bundle']['name'] == f'{name}.app'
    assert captured['entry'] == [launcher]
    assert captured['exe']['target_arch'] == 'arm64'
    assert 'pystray._darwin' in captured['analysis']['hiddenimports']
    assert 'floating_link_dock.macos_lifecycle' in captured['analysis']['hiddenimports']
    assert captured['analysis']['datas'] == [('public', 'customtkinter')]


@pytest.mark.parametrize('system,machine', [('Windows', 'ARM64'), ('Darwin', 'x86_64')])
def test_build_guard_refuses_other_platforms(system, machine, monkeypatch):
    import platform
    monkeypatch.setattr(platform, 'system', lambda: system)
    monkeypatch.setattr(platform, 'machine', lambda: machine)
    module = runpy.run_path(str(ROOT / 'scripts/build_macos.py'))
    with pytest.raises(SystemExit, match='Apple Silicon'):
        module['check_host']()
