from pathlib import Path
import subprocess

import pytest
from floating_link_dock import macos_integration as mi
from floating_link_dock.integration_types import BrowserChoice, IntegrationError


def test_installed_and_removed_browsers(monkeypatch, tmp_path):
    first, second = tmp_path / 'System', tmp_path / 'User'
    first.mkdir(); second.mkdir()
    for base, name in [(first, 'Safari.app'), (first, 'Google Chrome.app'), (second, 'Google Chrome.app')]:
        (base / name).mkdir()
    monkeypatch.setattr(mi, '_application_dirs', lambda: [first, second])
    assert [b.name for b in mi.installed_browsers()] == ['Safari', 'Chrome']
    (first / 'Safari.app').rmdir()
    assert [b.name for b in mi.installed_browsers()] == ['Chrome']


def test_browser_argv_preserves_spaces_and_ampersand(monkeypatch, tmp_path):
    app = tmp_path / 'Google Chrome.app'; app.mkdir()
    calls = []
    monkeypatch.setattr(mi.subprocess, 'run', lambda *args, **kw: calls.append((args, kw)))
    url = 'https://example.com/?a=1&b=2'
    mi.open_in_browser(url, BrowserChoice('Chrome', app))
    assert calls[0][0][0] == ['/usr/bin/open', '-a', str(app), url]
    assert calls[0][1]['check'] is True
    mi.open_in_default_browser(url)
    assert calls[1][0][0] == ['/usr/bin/open', url]


def test_rejected_url_and_missing_app_do_not_launch(monkeypatch, tmp_path):
    monkeypatch.setattr(mi.subprocess, 'run', lambda *a, **kw: pytest.fail('must not launch'))
    with pytest.raises(IntegrationError):
        mi.open_in_default_browser('javascript:alert(1)')
    with pytest.raises(IntegrationError):
        mi.open_in_browser('https://example.com', BrowserChoice('Chrome', tmp_path / 'missing.app'))


def test_launch_failure_is_readable(monkeypatch):
    def fail(*a, **kw):
        raise subprocess.CalledProcessError(1, a[0])
    monkeypatch.setattr(mi.subprocess, 'run', fail)
    with pytest.raises(IntegrationError, match='浏览器'):
        mi.open_in_default_browser('https://example.com')
