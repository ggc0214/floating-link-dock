"""Desktop verification of one exact scenes EXE; never touch an existing instance."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def windows(executable):
    found = []
    @callback_type
    def collect(hwnd, _):
        pid = wintypes.DWORD(); user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle: return True
        try:
            name = ctypes.create_unicode_buffer(32768); length = wintypes.DWORD(len(name))
            if not kernel32.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(length)): return True
            if Path(name.value).resolve() != executable.resolve(): return True
        finally: kernel32.CloseHandle(handle)
        title = ctypes.create_unicode_buffer(512); cls = ctypes.create_unicode_buffer(512); rect = wintypes.RECT()
        user32.GetWindowTextW(hwnd, title, len(title)); user32.GetClassNameW(hwnd, cls, len(cls))
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append(dict(hwnd=hwnd, pid=pid.value, title=title.value, cls=cls.value,
                          visible=bool(user32.IsWindowVisible(hwnd)),
                          rect=[rect.left, rect.top, rect.right, rect.bottom],
                          style=user32.GetWindowLongW(hwnd, -20)))
        return True
    user32.EnumWindows(collect, 0)
    return found


def main():
    executable = Path(sys.argv[1]).resolve()
    if executable.name != 'FloatingLinkDockScenes.exe': raise ValueError('Only scenes EXE can be verified')
    if windows(executable): raise RuntimeError('场景版已在运行，拒绝影响现有实例；请先自行退出。')
    base = Path(__file__).resolve().parents[1] / '.exe-test-data' / f'scenes-{time.time_ns()}'
    base.mkdir(parents=True)
    env = dict(os.environ, LOCALAPPDATA=str(base))
    process = subprocess.Popen([str(executable)], env=env)
    panel = None
    try:
        end = time.monotonic() + 25
        while time.monotonic() < end:
            found = windows(executable)
            panels = [w for w in found if w['visible'] and w['title'] == 'Floating Link Dock Scenes']
            trays = [w for w in found if 'SystemTrayIcon' in w['cls']]
            if panels:
                panel = panels[0]
                if panel['rect'][2] - panel['rect'][0] > 300 and trays: break
            time.sleep(.15)
        assert panel and panel['rect'][2] - panel['rect'][0] > 300, 'No expanded scene window'
        assert panel['style'] & 0x80 and not panel['style'] & 0x40000, 'Taskbar style wrong'
        assert trays, 'Tray missing'
        path = base / 'FloatingLinkDockScenes/scenes.json'
        document = json.loads(path.read_text(encoding='utf-8'))
        assert document['version'] == 2 and document['initialized']
        assert not document['settings']['launch_at_startup']
        assert not (base / 'FloatingLinkDock').exists()
        second = subprocess.run([str(executable)], env=env, timeout=15)
        assert second.returncode == 0
        assert len([w for w in windows(executable) if w['visible'] and w['title'] == 'Floating Link Dock Scenes']) == 1
        assert not (base / 'FloatingLinkDockScenes/errors.log').exists()
        user32.PostMessageW(panel['hwnd'], 0x10, 0, 0)
        process.wait(timeout=10)
        assert process.returncode == 0
        print(json.dumps(dict(expanded=True, tray=True, taskbar_hidden=True, independent_profile=True,
                              second_instance=True, exit_code=0, real_nas_tested=False), ensure_ascii=False))
    finally:
        if process.poll() is None:
            if panel: user32.PostMessageW(panel['hwnd'], 0x10, 0, 0)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Only this verifier's own exact process tree, never a user's instance.
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)


if __name__ == '__main__': main()
