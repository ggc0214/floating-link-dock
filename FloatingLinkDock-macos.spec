# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from pathlib import Path
import os
import runpy

minimum_system_version = runpy.run_path(
    str(Path(SPECPATH) / 'scripts/build_macos.py'))['minimum_system_version']
scenes = os.environ.get('FLOATING_LINK_DOCK_BUILD_SCENES') == '1'
name = 'FloatingLinkDockScenes' if scenes else 'FloatingLinkDock'
identifier = 'cn.floatinglinkdock.scenes' if scenes else 'cn.floatinglinkdock.app'

a = Analysis(
    ['launcher_scenes.py' if scenes else 'launcher.py'], pathex=['src'], binaries=[],
    datas=collect_data_files('customtkinter'),
    hiddenimports=['pystray._darwin', 'AppKit', 'Foundation', 'objc',
                   'PyObjCTools.MachSignals', 'floating_link_dock.macos_integration',
                   'floating_link_dock.macos_lifecycle'],
    excludes=['winreg', 'pystray._win32', 'IPython', 'jupyter', 'matplotlib',
              'numpy', 'pandas', 'pytest', 'scipy', 'sklearn', 'tensorflow', 'torch'],
    noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=name,
          debug=False, strip=False, upx=False, console=False, argv_emulation=False,
          target_arch='arm64', codesign_identity=None, entitlements_file=None)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=name)
app = BUNDLE(collection, name=f'{name}.app',
             icon='assets/scenes-macos.icns' if scenes else 'assets/app-macos.icns',
             bundle_identifier=identifier, info_plist={
                 'CFBundleIdentifier': identifier,
                 'CFBundleDisplayName': '工作场景' if scenes else '常用网址',
                 'CFBundleShortVersionString': '1.3.0',
                 'CFBundleVersion': '1.3.0',
                 'LSUIElement': True,
                 'LSMinimumSystemVersion': minimum_system_version(collection.name),
                 'NSHighResolutionCapable': True,
             })
