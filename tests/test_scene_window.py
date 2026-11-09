from types import SimpleNamespace
import json
import sys
import tkinter as tk
import time
import pytest
from floating_link_dock.scene_store import SceneStore
from floating_link_dock.scene_controller import SceneController
from floating_link_dock.scene_models import ResourceDraft
from floating_link_dock.scene_window import build_scenes_app
from floating_link_dock.resource_dispatch import ResourceDispatcher, open_windows_path
from test_app_smoke import FakeStartupManager


def make_app(tmp_path):
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    controller = SceneController(store); controller.initialize()
    controller.add_resource(ResourceDraft('url', '网站', 'example.com', True))
    calls = []
    dispatcher = ResourceDispatcher(lambda i: calls.append(i.id), lambda i: calls.append(i.id))
    return build_scenes_app(store, FakeStartupManager(), dispatcher), calls


@pytest.mark.skipif(sys.platform != 'win32', reason='requires real Windows paths')
def test_add_application_and_launch_alone_and_in_scene(tmp_path, monkeypatch):
    app, url_calls = make_app(tmp_path)
    program = tmp_path / 'My App.exe'
    program.touch()
    shortcut = tmp_path / 'My App.lnk'
    shortcut.touch()
    document = tmp_path / 'notes.txt'
    document.touch()
    started, files = [], []
    monkeypatch.setattr('floating_link_dock.resource_dispatch.subprocess.Popen',
                        lambda args, **kw: started.append((args, kw)))
    monkeypatch.setattr('floating_link_dock.resource_dispatch.os.startfile', files.append)
    app.dispatcher._open_path = open_windows_path

    def wait_for_open():
        deadline = time.monotonic() + 2
        while app._batch_context and time.monotonic() < deadline:
            app._poll_results()
            time.sleep(.01)
        assert not app._batch_context

    try:
        app.show_panel()
        app.snapshot = app.controller.duplicate_scene('Mixed scene')
        app.snapshot = app.controller.add_resource(ResourceDraft('file', 'Notes', str(document)))
        app._select_section('工作场景')
        app._configure_scene(app.snapshot.document.active_scene)
        for target in (program, shortcut):
            app.add_button.invoke()
            app.editor.kind_menu.set('应用')
            app.editor._kind_changed('应用')
            app.editor.name_entry.insert(0, target.stem)
            app.editor.target_entry.insert('1.0', f'"{target}"')
            app.editor._submit()
        scene = app.controller.store.load()[0].active_scene
        entry, shortcut_entry = scene.items[-2:]
        assert entry.kind == 'app' and entry.target == str(program)
        assert shortcut_entry.kind == 'app' and shortcut_entry.target == str(shortcut)
        backup = app.controller.store.root / 'backups' / 'before-app-entries.json'
        assert all(item['kind'] != 'app' for saved in json.loads(backup.read_text(encoding='utf-8'))['scenes']
                   for item in saved['items'])

        app._open_link(entry)
        wait_for_open()
        expected = ([str(program.resolve())], {'cwd': program.resolve().parent, 'shell': False})
        assert started == [expected]
        assert not url_calls and not files
        app._open_link(shortcut_entry)
        wait_for_open()
        assert files == [str(shortcut.resolve())]

        app._select_section('工作场景')
        app._launch_scene(scene)
        wait_for_open()
        assert started == [expected, expected]
        assert url_calls == [scene.items[0].id]
        assert sorted(files[1:]) == sorted([str(document), str(shortcut.resolve())])
    finally:
        app.destroy()


def test_scene_switch_only_shows(tmp_path):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel(); app.update()
        original = app.snapshot.document.active_scene_id
        app.snapshot = app.controller.create_scene('开发')
        app._render_expanded()
        app._select_section('常用网址')
        assert app.snapshot.document.active_scene_id == original and not calls
        assert app.title() == 'Floating Link Dock Scenes'
        app.toggle_expanded(); app.show_panel()
        assert app.is_expanded
    finally: app.destroy()


def test_drag_from_top_margin_moves_window_and_saves_position(tmp_path):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel()
        app.geometry('+120+120')
        app.update()
        start_x, start_y = app.winfo_x(), app.winfo_y()
        x, y = app.winfo_rootx() + 150, app.winfo_rooty() + 4
        strip = app.winfo_containing(x, y)
        strip.event_generate('<ButtonPress-1>', rootx=x, rooty=y)
        strip.event_generate('<B1-Motion>', rootx=x + 35, rooty=y + 24)
        app.update_idletasks()
        strip.event_generate('<ButtonRelease-1>', rootx=x + 35, rooty=y + 24)
        assert (app.winfo_x(), app.winfo_y()) == (start_x + 35, start_y + 24)
        settings = app.controller.store.load()[0].settings
        assert (settings.x, settings.y) == (app.winfo_x(), app.winfo_y())
        assert app.is_expanded and not calls
    finally:
        app.destroy()


def test_scene_tile_opens_all_openable_items_from_clicked_scene(tmp_path):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel()
        app.snapshot = app.controller.duplicate_scene('产品开发')
        for draft in [ResourceDraft('url', '飞书多维表', 'https://www.feishu.cn/base/demo'),
                      ResourceDraft('file', '成本', r'\\NAS\share\成本.xlsx'),
                      ResourceDraft('folder', '资料', r'\\NAS\share')]:
            app.snapshot = app.controller.add_resource(draft)
        scene = app.snapshot.document.active_scene
        app.snapshot = app.controller.create_scene('另一个')
        app._select_section('工作场景')
        assert len(app.board._items) == 2 and not calls
        click = SimpleNamespace(x_root=100, y_root=100)
        app.board._press(scene.id, click)
        app.board._release(click)
        deadline = time.monotonic() + 2
        while app._batch_context and time.monotonic() < deadline:
            app._poll_results(); app.update_idletasks(); time.sleep(.01)
        assert sorted(calls) == sorted(i.id for i in scene.items)
        assert '“产品开发”：已发出 4 项请求' in app.status_label.cget('text')
        assert app.snapshot.document.active_scene.name == '另一个'
    finally: app.destroy()


def test_scene_menu_edits_the_right_scene_without_opening(tmp_path, monkeypatch):
    app, calls = make_app(tmp_path); menus = []
    try:
        app.show_panel()
        app.snapshot = app.controller.create_scene('第一个')
        first = app.snapshot.document.active_scene
        app.snapshot = app.controller.create_scene('第二个')
        app._select_section('工作场景')
        monkeypatch.setattr(tk.Menu, 'tk_popup', lambda menu, *a: menus.append(menu))
        app.board._context_click(first.id, SimpleNamespace(x_root=10, y_root=10))
        menus[0].invoke(1)
        assert app.snapshot.document.active_scene == first and not calls
        app.add_button.invoke()
        app.editor.name_entry.insert(0, '新网址')
        app.editor.target_entry.insert('1.0', 'https://example.com')
        app.editor._submit()
        app._select_section('工作场景')
        badge = app.board._items[first.id][1].winfo_children()[0]
        assert badge.cget('text') == '1 项'
        assert not calls
    finally: app.destroy()


def test_scene_menu_renames_and_deletes_clicked_tile(tmp_path, monkeypatch):
    app, calls = make_app(tmp_path)
    menus = []
    try:
        app.show_panel()
        app.snapshot = app.controller.create_scene('目标场景')
        target = app.snapshot.document.active_scene
        app.snapshot = app.controller.create_scene('当前场景')
        active = app.snapshot.document.active_scene
        app._select_section('工作场景')
        monkeypatch.setattr(tk.Menu, 'tk_popup', lambda menu, *a: menus.append(menu))
        monkeypatch.setattr('floating_link_dock.scene_window.simpledialog.askstring',
                            lambda *args, **kwargs: '改名后的场景')
        event = SimpleNamespace(x_root=10, y_root=10)
        app.board._context_click(target.id, event)
        menus[-1].invoke('重命名场景')
        assert app.board._items[target.id][2].name == '改名后的场景'
        assert app.snapshot.document.active_scene == active
        assert not app._configuring_scene

        for confirm in (False, True):
            monkeypatch.setattr('floating_link_dock.scene_window.messagebox.askyesno',
                                lambda *args, **kwargs: confirm)
            app.board._context_click(target.id, event)
            menus[-1].invoke('删除场景')
            assert (target.id in app.board._items) is not confirm
        document = app.controller.store.load()[0]
        assert document.active_scene == active
        assert any(scene.name == '常用网址' for scene in document.scenes)
        assert not calls
    finally:
        app.destroy()


def test_drag_scene_tile_saves_position_without_launching_and_restores_after_restart(tmp_path):
    app, calls = make_app(tmp_path)
    store = app.controller.store
    try:
        app.snapshot = app.controller.duplicate_scene('第一个')
        first_id = app.snapshot.document.active_scene_id
        app.snapshot = app.controller.create_scene('第二个')
        second_id = app.snapshot.document.active_scene_id
    finally:
        app.destroy()

    raw = json.loads(store.path.read_text(encoding='utf-8'))
    for scene in raw['scenes']:
        del scene['x'], scene['y']
    store.path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')

    app = build_scenes_app(store, FakeStartupManager(), ResourceDispatcher(calls.append, calls.append))
    try:
        app.show_panel()
        app.update()
        board = app.board
        initial = board._positions[first_id]
        other = board._positions[second_id]
        assert initial != other
        start = SimpleNamespace(x_root=100, y_root=100)
        end = SimpleNamespace(x_root=100 + round(24 * board._scale), y_root=100 + round(16 * board._scale))
        board._press(first_id, start)
        board._motion(end)
        board._release(end)
        moved = board._positions[first_id]
        assert moved.x == initial.x + 24 and moved.y == initial.y + 16
        assert not calls and not app._batch_context
    finally:
        app.destroy()

    app = build_scenes_app(store, FakeStartupManager())
    try:
        app.show_panel()
        assert app.board._positions[first_id] == moved
        assert app.board._positions[second_id] == other
        assert app.snapshot.document.active_scene_id == second_id
    finally:
        app.destroy()
