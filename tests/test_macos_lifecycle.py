import plistlib
from queue import SimpleQueue
import sys
import time

import pytest
from floating_link_dock import macos_lifecycle as ml
from floating_link_dock.integration_types import IntegrationError


def test_startup_owns_only_its_plist(tmp_path):
    app = tmp_path / 'My Apps' / 'FloatingLinkDock.app'; app.mkdir(parents=True)
    agents = tmp_path / 'LaunchAgents'; agents.mkdir()
    unrelated = agents / 'other.plist'; unrelated.write_bytes(b'unchanged')
    manager = ml.StartupManager(app, agents_dir=agents)
    assert not manager.is_enabled()
    manager.set_enabled(True)
    assert manager.is_enabled()
    payload = plistlib.loads(manager.path.read_bytes())
    assert payload['ProgramArguments'] == ['/usr/bin/open', str(app)]
    assert payload['RunAtLoad'] is True
    manager.set_enabled(False)
    assert not manager.is_enabled()
    assert unrelated.read_bytes() == b'unchanged'


def test_source_cannot_enable_and_moved_app_can_repair(tmp_path):
    manager = ml.StartupManager(tmp_path / 'main.py', agents_dir=tmp_path / 'agents')
    with pytest.raises(IntegrationError, match='打包'):
        manager.set_enabled(True)
    first = tmp_path / 'First.app'; first.mkdir()
    old = ml.StartupManager(first, agents_dir=tmp_path / 'agents')
    old.set_enabled(True)
    second = tmp_path / 'Second.app'; second.mkdir()
    moved = ml.StartupManager(second, agents_dir=tmp_path / 'agents')
    assert not moved.is_enabled()
    assert moved.configuration_warning()
    moved.set_enabled(True)
    assert moved.is_enabled()
    assert not moved.configuration_warning()


def test_damaged_startup_configuration_is_nonfatal_and_repairable(tmp_path):
    app = tmp_path / 'FloatingLinkDock.app'; app.mkdir()
    manager = ml.StartupManager(app, agents_dir=tmp_path / 'agents')
    manager.path.parent.mkdir()
    manager.path.write_bytes(b'broken plist')
    assert not manager.is_enabled()
    assert manager.configuration_warning()
    assert manager.path.read_bytes() == b'broken plist'
    manager.set_enabled(False)
    manager.set_enabled(True)
    assert manager.is_enabled()


def test_unreadable_startup_configuration_warns_instead_of_exiting(monkeypatch, tmp_path):
    manager = ml.StartupManager(tmp_path / 'FloatingLinkDock.app', agents_dir=tmp_path)
    manager.path.touch()
    def fail():
        raise IntegrationError('无法读取开机启动设置')
    monkeypatch.setattr(manager, '_configuration', fail)
    assert not manager.is_enabled()
    assert '读取' in manager.configuration_warning()


def test_duplicate_request_reaches_queue(tmp_path):
    class Lock:
        def __init__(self): self.held = False
        def acquire(self, stream):
            if self.held: return False
            self.held = True; return True
        def release(self, stream): self.held = False
    lock = Lock()
    first = ml.SingleInstance(root=tmp_path, lock_api=lock)
    second = ml.SingleInstance(root=tmp_path, lock_api=lock)
    commands = SimpleQueue()
    try:
        assert first.acquire(lambda: None)
        first.bind_commands(commands)
        assert not second.acquire(lambda: None)
        deadline = time.monotonic() + 2
        while commands.empty() and time.monotonic() < deadline:
            time.sleep(.01)
        assert commands.get_nowait() == 'show'
    finally:
        second.close(); first.close()
    restarted = ml.SingleInstance(root=tmp_path, lock_api=lock)
    assert restarted.acquire(lambda: None)
    restarted.close()


@pytest.mark.skipif(sys.platform != 'darwin', reason='requires POSIX flock on Mac')
def test_real_process_lock_and_crash_recovery(tmp_path):
    import os
    import subprocess
    from pathlib import Path
    script = '''
import sys
from pathlib import Path
from floating_link_dock.macos_lifecycle import SingleInstance
g=SingleInstance(root=Path(sys.argv[1]))
print(g.acquire(lambda: None), flush=True)
sys.stdin.read()
'''
    env = dict(os.environ, PYTHONPATH=str(Path('src').resolve()))
    proc = subprocess.Popen([sys.executable, '-c', script, str(tmp_path)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    try:
        assert proc.stdout.readline().strip() == 'True'
        guard = ml.SingleInstance(root=tmp_path)
        assert not guard.acquire(lambda: None)
        guard.close()
        proc.kill(); proc.wait(timeout=5)
        guard = ml.SingleInstance(root=tmp_path)
        assert guard.acquire(lambda: None)
        guard.close()
    finally:
        if proc.poll() is None: proc.kill(); proc.wait(timeout=5)
