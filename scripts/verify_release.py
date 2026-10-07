"""Verify the actual EXE on the interactive Windows desktop, with isolated data."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import time


root = Path(__file__).resolve().parents[1]
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                              wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def windows():
    found = []

    @callback_type
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return True
        try:
            name = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(name))
            if not kernel32.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(length)):
                return True
            if Path(name.value).name.lower() != "floatinglinkdock.exe":
                return True
        finally:
            kernel32.CloseHandle(handle)
        title = ctypes.create_unicode_buffer(512)
        cls = ctypes.create_unicode_buffer(512)
        rect = wintypes.RECT()
        user32.GetWindowTextW(hwnd, title, len(title))
        user32.GetClassNameW(hwnd, cls, len(cls))
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        found.append(dict(hwnd=hwnd, pid=pid.value, title=title.value, cls=cls.value,
                          visible=bool(user32.IsWindowVisible(hwnd)),
                          rect=[rect.left, rect.top, rect.right, rect.bottom]))
        return True

    user32.EnumWindows(collect, 0)
    return found


if __name__ == "__main__":
    data_root = root / ".exe-test-data" / f"v11-{time.time_ns()}"
    data_root.mkdir(parents=True)
    env = dict(os.environ, LOCALAPPDATA=str(data_root))
    process = subprocess.Popen([str(root / "dist" / "FloatingLinkDock.exe")], env=env)
    panel = None
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            found = windows()
            panels = [w for w in found if w["title"] == "Floating Link Dock" and w["visible"]]
            trays = [w for w in found if "SystemTrayIcon" in w["cls"]]
            if panels and trays:
                panel = max(panels, key=lambda w: w["rect"][2] - w["rect"][0])
                if panel["rect"][2] - panel["rect"][0] > 300:
                    settings_path = data_root / "FloatingLinkDock" / "settings.json"
                    if settings_path.exists():
                        settings = json.loads(settings_path.read_text(encoding="utf-8"))
                        if settings["settings"].get("onboarding_complete"):
                            break
            time.sleep(0.2)
        assert panel is not None, f"No visible window: {found}"
        assert panel["rect"][2] - panel["rect"][0] > 300, panel
        assert trays, "Tray windows missing"
        settings = json.loads((data_root / "FloatingLinkDock" / "settings.json").read_text(encoding="utf-8"))
        assert settings["settings"]["onboarding_complete"]
        assert not (data_root / "FloatingLinkDock" / "errors.log").exists()
        report = dict(expanded_visible=True, tray_windows=len(trays), window=panel,
                      onboarding_saved=True, error_log=False)
        (data_root / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        if panel:
            user32.PostMessageW(panel["hwnd"], 0x10, 0, 0)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
