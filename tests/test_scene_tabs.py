import time
import customtkinter as ctk
import pytest
from floating_link_dock.scene_store import SceneStore
from floating_link_dock.scene_controller import SceneController
from floating_link_dock.scene_models import ResourceDraft
from test_scene_window import make_app


def test_common_and_work_tabs_are_separate_and_empty_work_does_not_show_common(tmp_path):
    app, calls = make_app(tmp_path)
    try:
        app.snapshot = app.controller.position_link(app.snapshot.links[0].id, 8, 900)
        app.show_panel()
        app.update()
        header = app.section_switch
        common_board = app.board
        common_board.canvas.yview_moveto(.4)
        scroll = common_board.canvas.yview()
        assert scroll[0] > 0
        assert app.section_switch.cget('values') == ['常用网址', '工作场景']
        assert app.section_switch.get() == '常用网址'
        common_ids = set(app.board._items)
        assert common_ids
        app._select_section('工作场景')
        app.update()
        work_board = app.board
        assert work_board.winfo_ismapped() and not common_board.winfo_ismapped()
        assert app.board._items == {}
        assert app.add_button.cget('text') == '＋ 场景'
        app._select_section('常用网址')
        app.update()
        assert app.section_switch is header and app.board is common_board
        assert common_board.winfo_ismapped() and not work_board.winfo_ismapped()
        assert common_board.canvas.yview() == scroll
        assert set(app.board._items) == common_ids and calls == []
        app._open_link(app.snapshot.links[0])
        end = time.monotonic() + 2
        while not calls and time.monotonic() < end: time.sleep(.01)
        app._poll_results()
        assert len(calls) == 1
    finally: app.destroy()


def test_cancel_add_removes_editor_and_reveals_existing_tiles(tmp_path):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel()
        board = app.board
        stored = app.controller.store.load()[0].scenes
        for _ in range(2):
            app.add_button.invoke()
            cancel = next(
                button for frame in app.editor.winfo_children()
                if isinstance(frame, ctk.CTkFrame)
                for button in frame.winfo_children()
                if isinstance(button, ctk.CTkButton) and button.cget('text') == '取消'
            )
            cancel.invoke()
            app.update()
            assert app.grid_slaves(row=2, column=0) == [board]
            assert board.winfo_ismapped() and board._items
        assert app.controller.store.load()[0].scenes == stored and not calls
    finally:
        app.destroy()


def test_create_scene_inside_work_keeps_common_resources_and_can_delete_last_work(tmp_path, monkeypatch):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel()
        common_items = app.snapshot.links
        app._select_section('工作场景')
        monkeypatch.setattr('floating_link_dock.scene_window.simpledialog.askstring', lambda *a, **kw: '产品开发')
        app.add_button.invoke()
        assert app.section_switch.get() == '工作场景'
        assert app.snapshot.document.active_scene.name == '产品开发'
        assert app.add_button.cget('text') == '＋ 添加'
        assert not app.snapshot.links
        app.snapshot = app.controller.add_resource(ResourceDraft('folder', '资料', r'\\NAS\share'))
        work_id = app.snapshot.document.active_scene_id
        app._select_section('常用网址')
        assert app.snapshot.links == common_items
        app._select_section('工作场景')
        assert set(app.board._items) == {work_id}
        app._configure_scene(app.snapshot.document.active_scene)
        assert len(app.board._items) == 1
        monkeypatch.setattr('floating_link_dock.scene_window.messagebox.askyesno', lambda *a, **kw: True)
        app._manage_scene('delete')
        assert app.section_switch.get() == '工作场景' and not app.board._items
        app._select_section('常用网址')
        assert app.snapshot.links == common_items and calls == []
    finally: app.destroy()


def test_cancel_new_scene_leaves_work_empty(tmp_path, monkeypatch):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel(); app._select_section('工作场景')
        monkeypatch.setattr('floating_link_dock.scene_window.simpledialog.askstring', lambda *a, **kw: None)
        app._manage_scene('create')
        assert len(app.snapshot.document.scenes) == 1 and app.board._items == {}
    finally: app.destroy()


def test_deleting_selected_work_scene_selects_another_work_not_common(tmp_path, monkeypatch):
    app, calls = make_app(tmp_path)
    try:
        app.show_panel(); app._select_section('工作场景')
        for name in ['开发一', '开发二']:
            monkeypatch.setattr('floating_link_dock.scene_window.simpledialog.askstring', lambda *a, n=name, **kw: n)
            app._manage_scene('create')
        monkeypatch.setattr('floating_link_dock.scene_window.messagebox.askyesno', lambda *a, **kw: True)
        app._manage_scene('delete')
        assert app.section_switch.get() == '工作场景'
        assert app.snapshot.document.active_scene.name == '开发一'
        assert set(app.board._items) == {app.snapshot.document.active_scene_id} and calls == []
    finally: app.destroy()


def test_ensure_common_scene_preserves_renamed_legacy_scene_and_positions(tmp_path, monkeypatch):
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    c = SceneController(store); c.initialize(); c.rename_scene('旧项目')
    c.add_resource(ResourceDraft('url', '原网址', 'example.com'))
    c.position_link(c.snapshot.links[0].id, 51, 93)
    before = c.snapshot
    monkeypatch.setattr(store, 'save', lambda doc: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError): c.ensure_common_scene()
    assert c.snapshot == before
    monkeypatch.undo()
    common_id = c.ensure_common_scene()
    assert c.snapshot.document.active_scene_id == before.document.active_scene_id
    assert c.snapshot.links == before.links and c.snapshot.links[0].x == 51
    assert c.ensure_common_scene() == common_id and len(c.snapshot.document.scenes) == 2
    assert store.load()[0].scenes[0].items == before.links
