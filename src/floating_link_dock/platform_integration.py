"""Lazy OS boundary: importing the Mac branch never imports Windows APIs."""
import importlib
import sys

from .integration_types import BrowserChoice, IntegrationError

_SERVICES = {
    'enable_dpi_awareness', 'get_work_area_for_point', 'get_cursor_work_area',
    'system_reduces_motion', 'installed_browsers', 'open_in_browser',
    'open_in_default_browser', 'StartupManager', 'SingleInstance',
    'activate_existing_window', 'show_startup_error',
}


def __getattr__(name):
    if name not in _SERVICES:
        raise AttributeError(name)
    if sys.platform == 'win32':
        backend = '.windows_integration'
    elif sys.platform == 'darwin':
        backend = '.macos_lifecycle' if name in {
            'StartupManager', 'SingleInstance', 'activate_existing_window'
        } else '.macos_integration'
    else:
        raise IntegrationError('当前仅支持 Windows 和 macOS')
    return getattr(importlib.import_module(backend, __package__), name)
