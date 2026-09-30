from __future__ import annotations

import ctypes
import subprocess
import sys
import webbrowser
from ctypes import wintypes
from pathlib import Path
from typing import Callable, Protocol

import winreg

from .geometry import Point, Rect
from .link_service import LinkValidationError, normalize_url


WINDOW_TITLE = "Floating Link Dock"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "FloatingLinkDock"


class IntegrationError(RuntimeError):
    """A safe, user-displayable Windows integration failure."""


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            return


class _Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", wintypes.DWORD),
    ]


def get_work_area_for_point(point: Point) -> Rect:
    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.argtypes = [_Point, wintypes.DWORD]
    user32.MonitorFromPoint.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    monitor = user32.MonitorFromPoint(_Point(point.x, point.y), 2)
    info = _MonitorInfo(cbSize=ctypes.sizeof(_MonitorInfo))
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise IntegrationError("无法获取屏幕工作区域")
    work = info.rcWork
    return Rect(work.left, work.top, work.right, work.bottom)


def get_cursor_work_area() -> Rect:
    user32 = ctypes.windll.user32
    point = _Point()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise IntegrationError("无法获取鼠标所在屏幕")
    return get_work_area_for_point(Point(point.x, point.y))


def _query_client_area_animation() -> bool:
    enabled = wintypes.BOOL()
    success = ctypes.windll.user32.SystemParametersInfoW(
        0x1042, 0, ctypes.byref(enabled), 0
    )
    if not success:
        raise OSError("SystemParametersInfoW failed")
    return bool(enabled.value)


def system_reduces_motion() -> bool:
    try:
        return not _query_client_area_animation()
    except (AttributeError, OSError):
        return False


def open_in_default_browser(url: str) -> None:
    try:
        normalized = normalize_url(url)
    except LinkValidationError as exc:
        raise IntegrationError(str(exc)) from exc
    try:
        opened = webbrowser.open_new_tab(normalized)
    except Exception as exc:
        raise IntegrationError("无法启动默认浏览器") from exc
    if not opened:
        raise IntegrationError("系统没有接受浏览器打开请求")


class StartupManager:
    def __init__(self, executable: Path, registry=winreg) -> None:
        self.executable = executable
        self._registry = registry

    @property
    def command(self) -> str:
        if self.executable.suffix.lower() == ".py":
            return subprocess.list2cmdline([sys.executable, str(self.executable)])
        return subprocess.list2cmdline([str(self.executable)])

    def is_enabled(self) -> bool:
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                self._registry.KEY_READ,
            ) as key:
                value, _kind = self._registry.QueryValueEx(key, RUN_VALUE)
            return value == self.command
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise IntegrationError("无法读取开机启动设置") from exc

    def set_enabled(self, enabled: bool) -> None:
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                self._registry.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    self._registry.SetValueEx(
                        key, RUN_VALUE, 0, self._registry.REG_SZ, self.command
                    )
                else:
                    try:
                        self._registry.DeleteValue(key, RUN_VALUE)
                    except FileNotFoundError:
                        pass
        except OSError as exc:
            raise IntegrationError("无法修改开机启动设置") from exc


class _MutexApi(Protocol):
    ERROR_ALREADY_EXISTS: int

    def create_mutex(self, name: str) -> int: ...

    def get_last_error(self) -> int: ...

    def close_handle(self, handle: int) -> None: ...


class _WinMutexApi:
    ERROR_ALREADY_EXISTS = 183

    def __init__(self) -> None:
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def create_mutex(self, name: str) -> int:
        return int(self._kernel32.CreateMutexW(None, False, name))

    @staticmethod
    def get_last_error() -> int:
        return ctypes.get_last_error()

    def close_handle(self, handle: int) -> None:
        self._kernel32.CloseHandle(handle)


class SingleInstance:
    def __init__(self, name: str = "Local\\FloatingLinkDock", api: _MutexApi | None = None) -> None:
        self._api = api or _WinMutexApi()
        self._name = name
        self._handle: int | None = None

    def acquire(self, on_second_instance: Callable[[], None]) -> bool:
        handle = self._api.create_mutex(self._name)
        if not handle:
            raise IntegrationError("无法创建程序实例锁")
        if self._api.get_last_error() == self._api.ERROR_ALREADY_EXISTS:
            self._api.close_handle(handle)
            on_second_instance()
            return False
        self._handle = handle
        return True

    def close(self) -> None:
        if self._handle is not None:
            self._api.close_handle(self._handle)
            self._handle = None

    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def activate_existing_window(title: str = WINDOW_TITLE) -> None:
    try:
        user32 = ctypes.windll.user32
        handle = user32.FindWindowW(None, title)
        if handle:
            user32.ShowWindow(handle, 9)
            user32.SetForegroundWindow(handle)
    except (AttributeError, OSError):
        return
