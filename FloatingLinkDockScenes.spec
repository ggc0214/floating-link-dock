# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(['launcher_scenes.py'], pathex=['src'], binaries=[],
             datas=collect_data_files('customtkinter'),
             hiddenimports=['pystray._win32', 'floating_link_dock.windows_integration'],
             excludes=['IPython', 'jupyter', 'matplotlib', 'numpy', 'pandas', 'pytest',
                       'scipy', 'sklearn', 'tensorflow', 'torch'],
             noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='FloatingLinkDockScenes',
          debug=False, strip=False, upx=True, console=False,
          bootloader_ignore_signals=False, disable_windowed_traceback=False,
          argv_emulation=False, target_arch=None, codesign_identity=None,
          entitlements_file=None, icon=['assets/scene.ico'])
