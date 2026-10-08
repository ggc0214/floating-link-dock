import os
from pathlib import Path
import subprocess
import sys

from floating_link_dock.storage import StoragePaths


def test_macos_import_does_not_load_winreg():
    script = '''
import sys
sys.platform = "darwin"
class Guard:
    def find_spec(self, fullname, *args):
        if fullname == "winreg":
            raise AssertionError("Mac imported winreg")
sys.meta_path.insert(0, Guard())
import floating_link_dock.platform_integration as integration
assert integration.IntegrationError
'''
    env = dict(os.environ, PYTHONPATH=str(Path('src').resolve()))
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_macos_data_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert StoragePaths.for_user().root == Path.home() / 'Library/Application Support/FloatingLinkDock'
    assert StoragePaths.for_user(tmp_path).root == tmp_path / 'FloatingLinkDock'
