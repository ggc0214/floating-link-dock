from pathlib import Path
from types import SimpleNamespace
import sys
import time

import pytest
from floating_link_dock import scene_models as models
from floating_link_dock import resource_dispatch
from floating_link_dock.macos_lifecycle import StartupManager
from floating_link_dock.scene_store import SceneStore


def test_scene_data_and_login_item_are_independent_on_mac(tmp_path, monkeypatch):
    monkeypatch.setattr('floating_link_dock.storage.sys', SimpleNamespace(platform='darwin'))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    store = SceneStore()
    assert store.root == tmp_path / 'Library/Application Support/FloatingLinkDockScenes'
    assert store.legacy_root == store.root.with_name('FloatingLinkDock')
    app = tmp_path / 'FloatingLinkDockScenes.app'
    app.mkdir()
    startup = StartupManager(app, agents_dir=tmp_path, label='cn.floatinglinkdock.scenes.launcher')
    startup.set_enabled(True)
    assert startup.is_enabled()
    assert StartupManager(app, agents_dir=tmp_path).path != startup.path


def test_mac_paths_and_apps_open_without_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(models, 'sys', SimpleNamespace(platform='darwin'), raising=False)
    document = tmp_path / '成本 & 明细.xlsx'
    document.touch()
    app = tmp_path / '微信.app'
    app.mkdir()
    (app / 'Contents').mkdir()
    (app / 'Contents/Info.plist').write_text('<plist><dict/></plist>', encoding='utf-8')
    calls = []
    monkeypatch.setattr(resource_dispatch.subprocess, 'run', lambda args, **kw: calls.append(args))
    for kind, path in [('folder', document), ('folder', tmp_path), ('app', app)]:
        resource_dispatch.open_macos_path(models.ResourceItem(kind, kind, '示例', path.as_posix().removeprefix(path.drive), 0))
    assert calls == [
        ['/usr/bin/open', str(document.resolve())],
        ['/usr/bin/open', '-a', 'Finder', str(tmp_path.resolve())],
        ['/usr/bin/open', str(app.resolve())],
    ]
    with pytest.raises(ValueError):
        resource_dispatch.open_macos_path(models.ResourceItem('a', 'folder', '应用', app.as_posix().removeprefix(app.drive), 0))


def test_mac_validates_mounted_paths_and_rejects_windows_shortcuts(monkeypatch):
    monkeypatch.setattr(models, 'sys', SimpleNamespace(platform='darwin'), raising=False)
    target = '/Volumes/团队共享/每周报告'
    assert models.validate_resource(models.ResourceDraft('folder', 'NAS', target)).target == target
    for kind, path in [('folder', 'smb://nas/share'), ('folder', 'relative/file'), ('app', '/tmp/旧入口.lnk')]:
        with pytest.raises(ValueError):
            models.validate_resource(models.ResourceDraft(kind, '错误路径', path))


@pytest.mark.skipif(sys.platform != 'darwin', reason='needs a logged-in Mac desktop')
def test_mac_scene_click_dispatches_web_document_and_app(tmp_path):
    from floating_link_dock.scene_controller import SceneController
    from floating_link_dock.scene_window import build_scenes_app
    from test_app_smoke import FakeStartupManager

    store = SceneStore(tmp_path / 'scenes', tmp_path / 'classic')
    controller = SceneController(store)
    controller.initialize()
    controller.create_scene('周报')
    for draft in [models.ResourceDraft('url', '网址', 'example.com'),
                  models.ResourceDraft('file', '周报', '/Volumes/共享/周报.xlsx'),
                  models.ResourceDraft('app', '浏览器', '/Applications/Safari.app')]:
        controller.add_resource(draft)
    opened = []
    dispatcher = resource_dispatch.ResourceDispatcher(opened.append, opened.append)
    app = build_scenes_app(store, FakeStartupManager(), dispatcher)
    try:
        app.show_panel()
        app._select_section('工作场景')
        scene = next(scene for scene in app.snapshot.document.scenes if scene.name == '周报')
        click = SimpleNamespace(x_root=100, y_root=100)
        app.board._press(scene.id, click)
        app.board._release(click)
        deadline = time.monotonic() + 2
        while app._batch_context and time.monotonic() < deadline:
            app._poll_results()
            app.update_idletasks()
            time.sleep(.01)
        assert {item.kind for item in opened} == {'url', 'file', 'app'}
        assert '已发出 3 项请求' in app.status_label.cget('text')
    finally:
        app.destroy()


@pytest.mark.skipif(sys.platform != 'darwin', reason='needs a logged-in Mac desktop')
def test_mac_add_scene_accepts_a_name_and_saves_it(tmp_path):
    import customtkinter as ctk
    import tkinter as tk

    from floating_link_dock.scene_window import build_scenes_app
    from test_app_smoke import FakeStartupManager

    store = SceneStore(tmp_path / 'scenes', tmp_path / 'classic')
    app = build_scenes_app(store, FakeStartupManager())

    def dismiss_old_dialog():
        for child in app.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()

    try:
        app.show_panel()
        app._select_section('工作场景')
        app.update()
        timer = app.after(250, dismiss_old_dialog)
        try:
            app.add_button.invoke()
        finally:
            app.after_cancel(timer)
        app.update()
        assert app.grab_current() is None
        entry = next((w for w in app._scene_tools.winfo_children()
                      if isinstance(w, ctk.CTkEntry)), None) if app._scene_tools else None
        assert entry is not None and entry.winfo_viewable()
        assert app.focus_get() is entry._entry
        entry.insert(0, '开发周报')
        entry._entry.event_generate('<Return>')
        app.update()
        assert app.snapshot.document.active_scene.name == '开发周报'
        assert store.load()[0].active_scene.name == '开发周报'
    finally:
        app.destroy()
