"""User-owned login item and POSIX single-instance lifecycle."""
from pathlib import Path
import os
import plistlib
import tempfile
import threading
import uuid

from .integration_types import IntegrationError
from .storage import StoragePaths

LABEL = 'cn.floatinglinkdock.launcher'


class StartupManager:
    def __init__(self, executable: Path, *, agents_dir: Path | None = None):
        self.executable = executable.absolute()
        self.path = (agents_dir or Path.home() / 'Library/LaunchAgents') / f'{LABEL}.plist'

    def _configuration(self):
        if not self.path.exists():
            return None
        try:
            with self.path.open('rb') as stream:
                return plistlib.load(stream)
        except (OSError, ValueError, plistlib.InvalidFileException) as exc:
            raise IntegrationError('无法读取开机启动设置，请关闭后重新启用') from exc

    def is_enabled(self) -> bool:
        try:
            configuration = self._configuration()
        except IntegrationError:
            return False
        return bool(isinstance(configuration, dict)
                    and configuration.get('ProgramArguments') == ['/usr/bin/open', str(self.executable)]
                    and configuration.get('RunAtLoad') is True)

    def configuration_warning(self):
        try:
            self._configuration()
        except IntegrationError:
            return '无法读取开机启动设置。网址盒仍可使用；请在菜单中关闭后重新启用，若失败请检查 LaunchAgents 目录权限。'
        if self.path.exists() and not self.is_enabled():
            return '应用位置或启动配置已更改，请重新启用开机启动。'
        return None

    def set_enabled(self, enabled: bool) -> None:
        if enabled and (self.executable.suffix != '.app' or not self.executable.is_dir()):
            raise IntegrationError('请先使用已打包的 .app，并放入 Applications 后再启用开机启动')
        temporary = None
        try:
            if not enabled:
                self.path.unlink(missing_ok=True)
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=LABEL, suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                plistlib.dump({'Label': LABEL, 'ProgramArguments': ['/usr/bin/open', str(self.executable)],
                              'RunAtLoad': True}, stream)
                stream.flush(); os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            temporary = None
        except OSError as exc:
            raise IntegrationError('无法修改开机启动设置，请检查用户目录权限') from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class _PosixLock:
    def acquire(self, stream):
        import fcntl
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def release(self, stream):
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _request_show(root):
    target = root / 'show.request'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix='show-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(uuid.uuid4().hex.encode('ascii'))
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def activate_existing_window() -> None:
    # SingleInstance already signals its own root; no Cocoa calls on worker threads.
    pass


class SingleInstance:
    def __init__(self, *, root: Path | None = None, lock_api=None):
        self.root = root or StoragePaths.for_user().root
        self._api = lock_api or _PosixLock()
        self._stream = None
        self._stop = threading.Event()
        self._listener = None
        self._last_request = None

    def _request_token(self):
        try:
            return (self.root / 'show.request').read_bytes()[:64]
        except FileNotFoundError:
            return None

    def acquire(self, on_second_instance) -> bool:
        if self._stream is not None:
            return True
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self._last_request = self._request_token()
            lock_path = self.root / 'instance.lock'
            if lock_path.is_symlink():
                raise IntegrationError('实例锁路径异常，请检查用户数据目录')
            stream = lock_path.open('a+b')
            try:
                acquired = self._api.acquire(stream)
            except Exception:
                stream.close()
                raise
            if not acquired:
                stream.close()
                _request_show(self.root)
                on_second_instance()
                return False
            self._stream = stream
            return True
        except OSError as exc:
            raise IntegrationError('无法创建程序实例锁或唤醒已有窗口') from exc

    def bind_commands(self, commands):
        if self._stream is None or self._listener is not None:
            return
        def listen():
            while not self._stop.wait(.1):
                try:
                    token = self._request_token()
                    if token != self._last_request:
                        self._last_request = token
                        if token is not None:
                            commands.put('show')
                except OSError:
                    continue
        self._listener = threading.Thread(target=listen, name='dock-wakeup', daemon=True)
        self._listener.start()

    def close(self):
        self._stop.set()
        if self._listener is not None:
            self._listener.join(timeout=1)
            self._listener = None
        if self._stream is not None:
            try:
                self._api.release(self._stream)
            finally:
                self._stream.close()
                self._stream = None
