"""Bounded daemon workers. Logical timeouts never claim to cancel native I/O."""
from collections import deque
from dataclasses import dataclass, replace
import os
from pathlib import Path
from stat import S_ISDIR, S_ISREG
import subprocess
import threading
from time import monotonic
from uuid import uuid4

from .scene_models import ResourceDraft, validate_resource


@dataclass(frozen=True)
class OpenResult:
    batch_id: str
    item_id: str
    name: str
    status: str
    message: str


def open_windows_path(item):
    if item.kind == 'app':
        draft = validate_resource(ResourceDraft('app', item.name, item.target, item.auto_open))
        try:
            program = Path(draft.target).resolve(strict=True)
            mode = program.stat().st_mode
        except OSError as exc:
            raise OSError('找不到应用，请重新选择程序或快捷方式') from exc
        validate_resource(replace(draft, target=str(program)))
        if not S_ISREG(mode):
            raise ValueError('请选择实际的 .exe 程序或 .lnk 快捷方式')
        if program.suffix.lower() == '.lnk':
            os.startfile(str(program))
        else:
            subprocess.Popen([str(program)], cwd=program.parent, shell=False)
        return

    draft = validate_resource(ResourceDraft('folder', item.name, item.target, item.auto_open))
    path = Path(draft.target)
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise OSError('无法访问路径，请检查文件或文件夹是否存在、访问权限及 NAS 连接') from exc
    if S_ISREG(mode):
        # Check the resolved file too, so a link cannot bypass the allowed file types.
        validate_resource(replace(draft, kind='file'))
        validate_resource(replace(draft, kind='file', target=str(path.resolve())))
    elif not S_ISDIR(mode):
        raise ValueError('此路径不是可打开的文件或文件夹')
    os.startfile(draft.target)


class ResourceDispatcher:
    def __init__(self, open_url, open_path, *, clock=monotonic, workers=4, timeout=10):
        if not 1 <= workers <= 4: raise ValueError('工作者数量须为1至4')
        self._open_url, self._open_path = open_url, open_path
        self._clock, self._timeout = clock, timeout
        self._condition = threading.Condition()
        self._jobs, self._results = deque(), deque()
        self._pending = {}
        self._batch = None
        self._running = 0
        self._closed = False
        self._threads = [threading.Thread(target=self._worker, daemon=True, name=f'scene-open-{n}') for n in range(workers)]
        for thread in self._threads: thread.start()

    @property
    def is_busy(self):
        with self._condition: return bool(self._pending)

    def submit(self, items):
        items = tuple(items)
        if not items: raise ValueError('没有可打开的项目')
        if len({i.id for i in items}) != len(items): raise ValueError('项目ID不能重复')
        for item in items:
            if item.kind == 'text': raise ValueError('文字请单击复制，不参与批量启动')
            validate_resource(ResourceDraft(item.kind, item.name, item.target, item.auto_open))
        with self._condition:
            self._expire()
            if self._closed: raise ValueError('打开服务已关闭')
            if self._pending: raise ValueError('正在启动，请等待当前任务完成')
            if self._running >= len(self._threads): raise ValueError('网络请求仍在处理中，请稍后重试；可退出场景版重新打开')
            self._batch = str(uuid4())
            deadline = self._clock() + self._timeout
            self._pending = {i.id: (i, deadline) for i in items}
            self._jobs.extend((self._batch, i) for i in items)
            self._condition.notify_all()
            return self._batch

    def _expire(self):
        now = self._clock()
        expired = {key for key, (_, deadline) in self._pending.items() if now >= deadline}
        for key in self._pending.copy():
            if key in expired:
                item, _ = self._pending.pop(key)
                self._results.append(OpenResult(self._batch, key, item.name, 'timeout',
                    '请求超时；已发出的系统请求不能强制取消，请检查连接后再决定是否重试'))
        if expired:
            self._jobs = deque((batch, item) for batch, item in self._jobs
                               if not (batch == self._batch and item.id in expired))

    def poll(self):
        with self._condition:
            self._expire()
            results = list(self._results); self._results.clear()
            return results

    def _worker(self):
        while True:
            with self._condition:
                while not self._jobs and not self._closed: self._condition.wait()
                if self._closed: return
                self._expire()
                if not self._jobs: continue
                batch, item = self._jobs.popleft()
                if batch != self._batch or item.id not in self._pending: continue
                self._running += 1
            status, message = 'requested', '已发出打开请求'
            try:
                (self._open_url if item.kind == 'url' else self._open_path)(item)
            except Exception as exc:
                status, message = 'failed', str(exc) or '系统未接受打开请求'
            with self._condition:
                self._running -= 1
                self._expire()
                if not self._closed and batch == self._batch and item.id in self._pending:
                    self._pending.pop(item.id)
                    self._results.append(OpenResult(batch, item.id, item.name, status, message))

    def close(self):
        with self._condition:
            self._closed = True
            self._jobs.clear(); self._pending.clear(); self._results.clear()
            self._condition.notify_all()
