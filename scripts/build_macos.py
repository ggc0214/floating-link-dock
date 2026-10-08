"""Native arm64 build; no cloud jobs, credentials or personal data are used."""
from pathlib import Path
import platform
import plistlib
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def minimum_system_version(directory):
    """Declare the actual minimum of collected, already-thinned arm64 binaries."""
    from PyInstaller.utils.osx import macosx_version_min
    minimum = (13, 0, 0)
    for path in Path(directory).rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic == b'\xcf\xfa\xed\xfe':
            minimum = max(minimum, macosx_version_min(str(path)))
    return '.'.join(map(str, minimum))


def check_host():
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('需要 Apple Silicon Mac 和原生 arm64 Python；拒绝跨平台构建。')
    if int(platform.mac_ver()[0].split('.')[0]) < 13:
        raise SystemExit('首版构建目标为 macOS 13 或更高版本。')


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    check_host()
    # The tests include Tk: run from a logged-in desktop, not a headless SSH job.
    run([sys.executable, '-m', 'pytest', '-q', '--basetemp=.test-macos-build'])
    build_icon = runpy.run_path(str(ROOT / 'scripts/generate_icon.py'))['build_icon']
    build_icon().save(ROOT / 'assets/app-macos.icns', format='ICNS')
    output = ROOT / 'dist/macos-arm64'
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
         '--distpath', str(output), '--workpath', str(ROOT / 'build/macos-arm64'),
         'FloatingLinkDock-macos.spec'])
    app = output / 'FloatingLinkDock.app'
    with (app / 'Contents/Info.plist').open('rb') as stream:
        metadata = plistlib.load(stream)
    if metadata.get('LSUIElement') is not True:
        raise SystemExit('打包失败：菜单栏应用属性不正确。')
    minimum = minimum_system_version(app)
    if metadata.get('LSMinimumSystemVersion') != minimum:
        raise SystemExit(f'打包失败：最低系统声明与依赖不符，实际需要 macOS {minimum}。')
    executable = app / 'Contents/MacOS/FloatingLinkDock'
    result = subprocess.run(['/usr/bin/lipo', '-archs', str(executable)], check=True,
                            capture_output=True, text=True)
    if result.stdout.strip() != 'arm64':
        raise SystemExit('打包失败：主程序不是纯 arm64。')
    run(['/usr/bin/file', str(executable)])
    # PyInstaller applies local ad-hoc signing. Verification is not notarization.
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)])
    archive = output / 'FloatingLinkDock-macos-arm64.zip'
    run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(archive)])
    print(f'构建与本地签名检查通过：{archive}\n此包最低系统：macOS {minimum}；尚需实机及另一台 Mac 验收；未做 Apple 公证。')


if __name__ == '__main__':
    main()
