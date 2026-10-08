# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from pathlib import Path
import runpy

minimum_system_version = runpy.run_path(
    str(Path(SPECPATH) / 'scripts/build_macos.py'))['minimum_system_version']

a = Analysis(
    ['launcher.py'], pathex=['src'], binaries=[],
    datas=collect_data_files('customtkinter'),
    hiddenimports=['pystray._darwin', 'AppKit', 'Foundation', 'objc',
                   'PyObjCTools.MachSignals', 'floating_link_dock.macos_integration',
                   'floating_link_dock.macos_lifecycle'],
    excludes=['winreg', 'pystray._win32', 'IPython', 'jupyter', 'matplotlib',
              'numpy', 'pandas', 'pytest', 'scipy', 'sklearn', 'tensorflow', 'torch'],
    noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FloatingLinkDock',
          debug=False, strip=False, upx=False, console=False, argv_emulation=False,
          target_arch='arm64', codesign_identity=None, entitlements_file=None)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FloatingLinkDock')
app = BUNDLE(collection, name='FloatingLinkDock.app', icon='assets/app-macos.icns',
             bundle_identifier='cn.floatinglinkdock.app', info_plist={
                 'CFBundleIdentifier': 'cn.floatinglinkdock.app',
                 'CFBundleDisplayName': '常用网址',
                 'CFBundleShortVersionString': '1.3.0',
                 'CFBundleVersion': '1.3.0',
                 'LSUIElement': True,
                 'LSMinimumSystemVersion': minimum_system_version(collection.name),
                 'NSHighResolutionCapable': True,
             })
