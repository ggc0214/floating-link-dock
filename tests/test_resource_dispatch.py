from dataclasses import replace
import sys
import threading
import time
import pytest
from floating_link_dock.resource_dispatch import ResourceDispatcher, open_windows_path
from floating_link_dock.scene_models import ResourceItem


def item(key='a', kind='url'):
    return ResourceItem(key, kind, key, 'https://example.com' if kind == 'url' else r'\\NAS\share\表.xlsx', 0, 8, 8, True)


def collect(dispatcher, count, seconds=2):
    output = []; end = time.monotonic() + seconds
    while len(output) < count and time.monotonic() < end:
        output.extend(dispatcher.poll()); time.sleep(.005)
    return output


def test_mixed_failure_does_not_stop_and_busy_rejects():
    called = []; gate = threading.Event()
    def url(i):
        gate.wait(1); called.append(i.id)
        if i.id == 'bad': raise OSError('打开失败')
    d = ResourceDispatcher(url, lambda i: called.append(i.id), workers=1)
    try:
        d.submit([item('bad'), item('ok'), item('file', 'file')])
        with pytest.raises(ValueError): d.submit([item()])
        gate.set()
        results = collect(d, 3)
        assert {r.item_id: r.status for r in results} == {'bad': 'failed', 'ok': 'requested', 'file': 'requested'}
        assert called == ['bad', 'ok', 'file'] and not d.is_busy
    finally: gate.set(); d.close()


def test_stalled_nas_timeout_cancels_queued_and_close_never_waits():
    gate = threading.Event(); entered = threading.Event(); calls = []
    now = [0.0]
    def stalled(i):
        calls.append(i.id); entered.set(); gate.wait(2)
    d = ResourceDispatcher(stalled, stalled, workers=1, timeout=10, clock=lambda: now[0])
    try:
        d.submit([item('blocked'), item('queued')]); assert entered.wait(1)
        now[0] = 11
        assert [r.status for r in d.poll()] == ['timeout', 'timeout']
        with pytest.raises(ValueError): d.submit([item('retry')])
        start = time.monotonic(); d.close()
        assert time.monotonic() - start < .2
        gate.set(); time.sleep(.05)
        assert calls == ['blocked'] and d.poll() == []
    finally: gate.set(); d.close()


def test_batch_over_twenty_and_text_never_dispatch():
    calls = []; d = ResourceDispatcher(lambda i: calls.append(i), lambda i: calls.append(i))
    try:
        with pytest.raises(ValueError): d.submit([item('t', 'text')])
        assert calls == []
        d.submit([item(str(i)) for i in range(21)])
        assert len(collect(d, 21)) == len(calls) == 21
        assert len(d._threads) == 4 and all(t.daemon for t in d._threads)
    finally: d.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='requires real Windows paths')
def test_windows_open_identifies_path_and_blocks_unsupported_files(tmp_path, monkeypatch):
    import os
    calls = []
    monkeypatch.setattr(os, 'startfile', lambda path: calls.append(path), raising=False)
    folder = tmp_path / '资料.xlsx'
    folder.mkdir()
    file = tmp_path / '表 & 价格.xlsx'
    file.touch()
    blocked = tmp_path / '程序.exe'
    blocked.touch()
    for kind, target in [('file', folder), ('folder', file)]:
        open_windows_path(replace(item(kind=kind), target=str(target)))
    with pytest.raises(ValueError, match='文件类型'):
        open_windows_path(replace(item(kind='folder'), target=str(blocked)))
    with pytest.raises(OSError, match='连接|权限'):
        open_windows_path(replace(item(kind='folder'), target=str(tmp_path / '不存在')))
    assert calls == [str(folder), str(file)]
