from pathlib import Path
from types import SimpleNamespace
import tkinter as tk

import pytest
import sys

if sys.platform == 'win32':
    import floating_link_dock.windows_integration as wi
from floating_link_dock.integration_types import BrowserChoice
from floating_link_dock.models import Link
from floating_link_dock.window import build_app
from test_app_smoke import FakeStore, FakeStartupManager


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows browser detection')
def test_browser_choice_api_is_available():
    assert hasattr(wi, 'installed_browsers')


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows browser detection')
def test_detection_checks_existence_and_deduplicates(monkeypatch, tmp_path):
    chrome = tmp_path / 'Google/Chrome/Application/chrome.exe'
    chrome.parent.mkdir(parents=True)
    chrome.touch()
    monkeypatch.setattr(wi, '_registered_browser_path', lambda exe: chrome if exe == 'chrome.exe' else None)
    for variable in ('LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)'):
        monkeypatch.setenv(variable, str(tmp_path))
    choices = wi.installed_browsers()
    assert [(b.name, b.executable) for b in choices] == [('Chrome', chrome)]
    chrome.unlink()
    assert wi.installed_browsers() == []


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows process launching')
def test_selected_browser_receives_normalized_url_as_one_argument(monkeypatch, tmp_path):
    executable = tmp_path / 'Browser With Spaces.exe'
    executable.touch()
    browser = wi.BrowserChoice('Chrome', executable)
    launched = []
    monkeypatch.setattr(wi.subprocess, 'Popen', lambda args, **kwargs: launched.append((args, kwargs)))
    wi.open_in_browser('example.com/a?q=hello&b=2', browser)
    assert launched == [([str(executable), 'https://example.com/a?q=hello&b=2'], {'shell': False})]
    with pytest.raises(wi.IntegrationError):
        wi.open_in_browser('javascript:alert(1)', browser)
    executable.unlink()
    with pytest.raises(wi.IntegrationError):
        wi.open_in_browser('https://example.com', browser)
    assert len(launched) == 1


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows process launching')
def test_browser_launch_failure_has_readable_error(monkeypatch, tmp_path):
    executable = tmp_path / 'chrome.exe'
    executable.touch()
    def fail(*args, **kwargs):
        raise OSError('unavailable')
    monkeypatch.setattr(wi.subprocess, 'Popen', fail)
    with pytest.raises(wi.IntegrationError, match='Chrome'):
        wi.open_in_browser('https://example.com', wi.BrowserChoice('Chrome', executable))


def test_tile_menu_opens_current_link_in_selected_browser(monkeypatch):
    link = Link('one', '示例', 'https://example.com', 0, 8, 8)
    app = build_app(FakeStore([link]), FakeStartupManager())
    menus = []
    monkeypatch.setattr(tk.Menu, 'tk_popup', lambda menu, *args: menus.append(menu))
    import floating_link_dock.tile_board as board_module
    choices = [BrowserChoice('Chrome', Path('chrome.exe')), BrowserChoice('Edge', Path('msedge.exe'))]
    monkeypatch.setattr(board_module, 'installed_browsers', lambda: choices)
    opened = []
    try:
        app.show_panel()
        app.board._on_open_browser = lambda chosen_link, browser: opened.append((chosen_link, browser))
        app.board._menu(link.id, SimpleNamespace(x_root=300, y_root=300))
        menu = menus[0]
        labels = [menu.entrycget(i, 'label') for i in range(menu.index('end') + 1)
                  if menu.type(i) == 'command']
        assert labels == ['示例', '使用默认浏览器打开', '使用 Chrome 打开', '使用 Edge 打开', '编辑', '删除']
        for i in range(menu.index('end') + 1):
            if menu.type(i) == 'command' and menu.entrycget(i, 'label') in ('使用 Chrome 打开', '使用 Edge 打开'):
                menu.invoke(i)
        assert opened == [(link, choices[0]), (link, choices[1])]
    finally:
        app.destroy()
