"""macOS system services; Cocoa is loaded only when a native service is used."""
from pathlib import Path
import subprocess
import sys

from .integration_types import BrowserChoice, IntegrationError
from .link_service import LinkValidationError, normalize_url
from .geometry import Point, Rect


def _application_dirs():
    return [Path('/System/Applications'), Path('/Applications'), Path.home() / 'Applications']


def installed_browsers() -> list[BrowserChoice]:
    choices = []
    for name, bundle in [('Safari', 'Safari.app'), ('Chrome', 'Google Chrome.app'),
                         ('Edge', 'Microsoft Edge.app'), ('Firefox', 'Firefox.app')]:
        for directory in _application_dirs():
            candidate = directory / bundle
            if candidate.is_dir():
                choices.append(BrowserChoice(name, candidate))
                break
    return choices


def _validated_url(url):
    try:
        return normalize_url(url)
    except LinkValidationError as exc:
        raise IntegrationError(str(exc)) from exc


def _open(arguments):
    try:
        subprocess.run(['/usr/bin/open', *arguments], check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise IntegrationError('无法启动浏览器，请检查应用是否安装或已被移动') from exc


def open_in_default_browser(url: str) -> None:
    _open([_validated_url(url)])


def open_in_browser(url: str, browser: BrowserChoice) -> None:
    normalized = _validated_url(url)
    if not browser.executable.is_dir():
        raise IntegrationError(f'找不到 {browser.name}，请重新选择浏览器')
    _open(['-a', str(browser.executable), normalized])


def show_startup_error(message: str) -> None:
    try:
        from AppKit import NSAlert, NSApplication
        NSApplication.sharedApplication()
        alert = NSAlert.alloc().init()
        alert.setMessageText_('常用网址 · 启动失败')
        alert.setInformativeText_(message)
        alert.runModal()
    except Exception:
        # A missing/broken Cocoa bridge must not obscure the original failure.
        print(message, file=sys.stderr)


def enable_dpi_awareness() -> None:
    # Tk/Cocoa coordinates are logical points; do not multiply by Retina scale.
    pass


def cocoa_to_tk(frame, primary_top: float) -> Rect:
    x, y, width, height = frame
    return Rect(round(x), round(primary_top - y - height),
                round(x + width), round(primary_top - y))


def _frame_tuple(frame):
    return frame.origin.x, frame.origin.y, frame.size.width, frame.size.height


def _screens():
    try:
        from AppKit import NSApplication, NSScreen
        NSApplication.sharedApplication()
        screens = list(NSScreen.screens())
        if not screens:
            raise IntegrationError('无法获取屏幕工作区域')
        first = _frame_tuple(screens[0].frame())
        return screens, first[1] + first[3]
    except (ImportError, RuntimeError) as exc:
        raise IntegrationError('无法获取 Mac 屏幕信息，请检查 Cocoa 依赖') from exc


def _screen_rects():
    screens, top = _screens()
    return [(cocoa_to_tk(_frame_tuple(s.frame()), top),
             cocoa_to_tk(_frame_tuple(s.visibleFrame()), top)) for s in screens]


def get_work_area_for_point(point: Point) -> Rect:
    screens = _screen_rects()
    for frame, work in screens:
        if frame.left <= point.x < frame.right and frame.top <= point.y < frame.bottom:
            return work
    def distance(entry):
        work = entry[1]
        dx = max(work.left - point.x, 0, point.x - work.right)
        dy = max(work.top - point.y, 0, point.y - work.bottom)
        return dx * dx + dy * dy
    return min(screens, key=distance)[1]


def get_cursor_work_area() -> Rect:
    try:
        from AppKit import NSEvent
        _, top = _screens()
        mouse = NSEvent.mouseLocation()
        return get_work_area_for_point(Point(round(mouse.x), round(top - mouse.y)))
    except ImportError as exc:
        raise IntegrationError('无法获取鼠标所在屏幕') from exc


def system_reduces_motion() -> bool:
    try:
        from AppKit import NSWorkspace
        return bool(NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion())
    except (ImportError, AttributeError):
        return False
