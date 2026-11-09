from types import SimpleNamespace
import tkinter as tk
import customtkinter as ctk
from floating_link_dock.scene_widgets import ResourceBoard, ResourceEditor
from floating_link_dock.scene_models import ResourceItem


def test_resource_editor_keeps_multiline_text_and_clears_auto():
    root = ctk.CTk(); output = []
    try:
        editor = ResourceEditor(root, item=ResourceItem('a', 'text', '话术', '第一行\n第二行', 0, auto_open=True),
                                on_save=output.append, on_cancel=lambda: None)
        editor._submit()
        assert output[0].kind == 'text' and output[0].target == '第一行\n第二行'
        assert not output[0].auto_open
    finally: root.destroy()


def test_picker_cancel_preserves_path(monkeypatch):
    root = ctk.CTk()
    try:
        monkeypatch.setattr('floating_link_dock.scene_widgets.filedialog.askopenfilename', lambda **kw: '')
        editor = ResourceEditor(root, item=ResourceItem('a', 'file', '成本', r'\\NAS\share\成本.xlsx', 0),
                                on_save=lambda i: None, on_cancel=lambda: None)
        assert editor.kind_menu.get() == '文件 / 文件夹'
        editor.browse_buttons[0].invoke()
        assert editor.target_entry.get('1.0', 'end-1c') == r'\\NAS\share\成本.xlsx'
    finally: root.destroy()


def test_non_url_menu_does_not_detect_browsers(monkeypatch):
    root = ctk.CTk(); menus = []; opened = []
    try:
        item = ResourceItem('a', 'folder', '资料', r'\\NAS\share', 0, 8, 8)
        board = ResourceBoard(root, [item], on_open=opened.append, on_edit=lambda i: None,
                              on_delete=lambda i: None, on_position=lambda *a: None)
        monkeypatch.setattr(tk.Menu, 'tk_popup', lambda menu, *a: menus.append(menu))
        monkeypatch.setattr('floating_link_dock.scene_widgets.installed_browsers', lambda: (_ for _ in ()).throw(AssertionError()))
        board._context_click('a', SimpleNamespace(x_root=200, y_root=200))
        labels = [menus[0].entrycget(i, 'label') for i in range(menus[0].index('end') + 1) if menus[0].type(i) == 'command']
        assert not any('浏览器' in label for label in labels)
        menus[0].invoke(1)
        assert opened == [item] and board._active is None
    finally: root.destroy()
