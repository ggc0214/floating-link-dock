from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk

from . import theme
from .window import FloatingDockWindow
from .scene_controller import SceneController
from .scene_models import ResourceItem
from .scene_widgets import ResourceBoard, ResourceEditor, SceneBoard
from .resource_dispatch import ResourceDispatcher, open_windows_path
from .platform_integration import open_in_default_browser, open_in_browser
from .scene_main import TITLE, APP_ID, report_scene_error
from .scene_icons import build_scene_icon, SCENE_ACCENT, SCENE_HOVER, SCENE_BORDER


@dataclass(frozen=True)
class BrowserOpenItem(ResourceItem):
    browser: object = None


def open_url_item(item):
    browser = getattr(item, 'browser', None)
    if browser is None: open_in_default_browser(item.target)
    else: open_in_browser(item.target, browser)


class ScenesWindow(FloatingDockWindow):
    _floating_color = SCENE_ACCENT
    _floating_hover = SCENE_HOVER
    _floating_border = SCENE_BORDER

    def _build_mark(self):
        return build_scene_icon()

    def __init__(self, controller, startup, dispatcher=None):
        self._common_scene_id = controller.ensure_common_scene()
        document = controller.snapshot.document
        self._section = '常用网址' if document.active_scene_id == self._common_scene_id else '工作场景'
        self._configuring_scene = False
        self.dispatcher = dispatcher or ResourceDispatcher(open_url_item, open_windows_path)
        self._batch_context = {}
        self._status_text = ''
        self._closed = False
        super().__init__(controller, startup)
        self.title(TITLE)

    def _button(self, parent, text, command, width=60):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=30,
                             font=(theme.SCENE_FONT, 13),
                             fg_color=theme.SURFACE_RAISED, hover_color=theme.SURFACE_HOVER,
                             text_color=theme.TEXT, corner_radius=10, border_width=1, border_color=theme.BORDER)

    def _build_panel(self):
        self._clear(); self.is_expanded = True
        self._section_boards = {}
        self._content = None
        self._scene_tools = None
        for row in (0, 1, 3): self.grid_rowconfigure(row, weight=0)
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew')
        header.grid_columnconfigure(0, weight=1)
        controls = ctk.CTkFrame(header, fg_color='transparent')
        controls.grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 6))
        controls.grid_columnconfigure(1, weight=1)
        grip = ctk.CTkLabel(controls, text='', image=self._header_face, width=38, height=38,
                            fg_color=SCENE_ACCENT, corner_radius=11)
        grip.grid(row=0, column=0, padx=(0, 8))
        self.section_switch = ctk.CTkSegmentedButton(controls, values=['常用网址', '工作场景'],
                    command=self._select_section, width=164, height=32, dynamic_resizing=False,
                    font=(theme.SCENE_FONT, 12, 'bold'), text_color=theme.TEXT,
                    fg_color=theme.SURFACE_RAISED, selected_color=theme.ACCENT,
                    selected_hover_color=theme.ACCENT_HOVER, unselected_color=theme.SURFACE_RAISED,
                    unselected_hover_color=theme.SURFACE_HOVER)
        self.section_switch.grid(row=0, column=1, sticky='ew')
        self.add_button = self._button(controls, '＋ 添加', self._add_to_current_view, 64)
        self.add_button.grid(row=0, column=2, padx=4)
        self._button(controls, '−', self.toggle_expanded, 28).grid(row=0, column=3)
        for widget in (header, controls, grip):
            widget.bind('<ButtonPress-1>', self._drag_press)
            widget.bind('<B1-Motion>', self._drag_motion_expanded)
            widget.bind('<ButtonRelease-1>', self._drag_release_grip if widget is grip else self._drag_release_expanded)
            self._bind_context_menu(widget)
        self.status_label = ctk.CTkLabel(self, text='', height=34, wraplength=340,
                                        font=(theme.SCENE_FONT, 10), text_color=theme.TEXT_MUTED)
        self.status_label.grid(row=3, column=0, padx=12, pady=(0, 5), sticky='ew')
        for section in ('常用网址', '工作场景'):
            self._section_board(section)

    def _add_to_current_view(self):
        if self._section == '工作场景' and not self._configuring_scene:
            self._manage_scene('create')
        else:
            self._begin_add()

    def _render_expanded(self):
        if not self.is_expanded:
            self._build_panel()
        work_board = self._section == '工作场景' and not self._configuring_scene
        self.section_switch.set(self._section)
        self.add_button.configure(text='＋ 场景' if work_board else '＋ 添加')
        if self._scene_tools is not None:
            self._scene_tools.destroy()
            self._scene_tools = None
        if self._configuring_scene:
            tools = ctk.CTkFrame(self, fg_color='transparent')
            self._scene_tools = tools
            tools.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 6))
            tools.grid_columnconfigure(1, weight=1)
            self._button(tools, '‹ 返回', lambda: self._select_section('工作场景'), 60).grid(row=0, column=0)
            ctk.CTkLabel(tools, text=self.snapshot.document.active_scene.name, wraplength=180,
                         font=(theme.SCENE_FONT, 13, 'bold'), text_color=theme.TEXT).grid(row=0, column=1, padx=6)
            self._button(tools, '管理', self._scene_menu, 48).grid(row=0, column=2)
        if self._show_editor:
            # Own the scrollbar and its outer frame so closing the editor removes both.
            content = ctk.CTkFrame(self, fg_color='transparent')
            content.grid_columnconfigure(0, weight=1)
            content.grid_rowconfigure(0, weight=1)
            scroll = ctk.CTkScrollableFrame(content, fg_color=theme.BACKGROUND)
            scroll.grid(row=0, column=0, sticky='nsew')
            scroll.grid_columnconfigure(0, weight=1)
            self.editor = ResourceEditor(scroll, item=self._editing, on_save=self._save_editor,
                                         on_cancel=self._cancel_editor, in_scene=self._configuring_scene)
            self.editor.grid(row=0, column=0, sticky='ew')
        else:
            self.board = (self._resource_board(self.snapshot.links, '这个场景还没有项目')
                          if self._configuring_scene else self._section_board(self._section))
            content = self.board
        previous = self._content
        if self._show_editor:
            content.grid(row=2, column=0, sticky='nsew', padx=8)
        else:
            content.grid(row=2, column=0, sticky='nsew', padx=(12, 8), pady=(0, 4))
        if previous is not None and previous is not content and previous.winfo_exists():
            if any(previous is board for _, board in self._section_boards.values()):
                previous.grid_remove()
            else:
                previous.destroy()
        self._content = content
        hint = ('点击启动 · 按住拖动 · 右键编辑' if work_board else
                '点击“＋ 添加”配置项目，完成后点“返回”。' if self._configuring_scene else
                '点击打开 · 按住方块拖动调整位置')
        self.status_label.configure(text=self._status_text or hint)

    def _resource_board(self, items, empty_text):
        board = ResourceBoard(self, items, on_open=self._open_link, on_edit=self._begin_edit,
                              on_delete=self._delete_link, on_position=self._position_link,
                              on_open_browser=self._open_link_in_browser)
        if not items:
            label = ctk.CTkLabel(board.canvas, text=f'{empty_text}\n点右上角“＋ 添加”开始',
                                 text_color=theme.TEXT_MUTED, font=(theme.SCENE_FONT, 13))
            label.place(relx=.5, rely=.4, anchor='center')
        return board

    def _section_board(self, section):
        work = section == '工作场景'
        items = self._work_scenes() if work else self._common_links()
        cached = self._section_boards.get(section)
        if cached and cached[0] == items:
            return cached[1]
        if work:
            board = SceneBoard(self, items, on_open=self._launch_scene, on_edit=self._configure_scene,
                               on_position=self._position_scene, on_manage=self._manage_scene)
        else:
            board = self._resource_board(items, '还没有常用入口')
        self._section_boards[section] = (items, board)
        if cached and cached[1] is not self._content:
            cached[1].destroy()
        return board

    def _common_links(self):
        return next(s.items for s in self.snapshot.document.scenes if s.id == self._common_scene_id)

    def _work_scenes(self):
        return tuple(s for s in self.snapshot.document.scenes if s.id != self._common_scene_id)

    def _position_scene(self, scene_id, x, y):
        self.snapshot = self.controller.position_scene(scene_id, x, y)
        self._section_boards['工作场景'] = (self._work_scenes(), self.board)

    def _position_link(self, link_id, x, y):
        super()._position_link(link_id, x, y)
        if self._section == '常用网址':
            self._section_boards['常用网址'] = (self._common_links(), self.board)

    def _select_section(self, section):
        if section not in {'常用网址', '工作场景'}: return
        previous = self._section
        try:
            current = self.snapshot.document.active_scene_id
            scenes = self._work_scenes()
            target = self._common_scene_id if section == '常用网址' else (
                current if current != self._common_scene_id or not scenes else scenes[0].id)
            if target != current:
                self.snapshot = self.controller.select_scene(target)
            self._section = section
            self._configuring_scene = False
            self._show_editor = False; self._editing = None
            self._status_text = ''
            self._render_expanded()
        except (OSError, ValueError) as exc:
            self.section_switch.set(previous); self._error(exc)

    def _configure_scene(self, scene):
        try:
            if scene.id != self.snapshot.document.active_scene_id:
                self.snapshot = self.controller.select_scene(scene.id)
            self._configuring_scene = True
            self._show_editor = False; self._editing = None
            self._status_text = ''
            self._render_expanded()
        except (OSError, ValueError) as exc: self._error(exc)

    def _scene_menu(self):
        menu = tk.Menu(self, tearoff=False, font=(theme.SCENE_FONT, 11))
        for label, action in [('重命名', 'rename'), ('复制场景', 'duplicate'), ('删除场景', 'delete')]:
            menu.add_command(label=label, command=lambda a=action: self._manage_scene(a))
        try: menu.tk_popup(*self.winfo_pointerxy())
        finally: menu.grab_release()

    def _manage_scene(self, action, scene_id=None):
        document = self.snapshot.document
        try:
            current = (document.active_scene if scene_id is None else
                       next((scene for scene in document.scenes if scene.id == scene_id), None))
            if current is None:
                raise ValueError('找不到该场景')
            if current.id == self._common_scene_id and action in {'rename', 'delete', 'duplicate'}:
                raise ValueError('常用网址页单独保留，请在工作场景中管理场景')
            if action == 'delete':
                if not messagebox.askyesno('删除场景', f'删除“{current.name}”？只删除入口，不删除文件。', parent=self): return
                remaining_work = [s for s in self._work_scenes() if s.id != current.id]
                fallback = remaining_work[0].id if remaining_work else self._common_scene_id
                self.snapshot = self.controller.delete_scene(current.id, fallback_scene_id=fallback)
            else:
                titles = {'create': '新建场景', 'rename': '重命名场景', 'duplicate': '复制场景'}
                name = simpledialog.askstring(titles[action], '场景名称', parent=self,
                         initialvalue=current.name if action == 'rename' else '')
                if name is None: return
                if action == 'rename':
                    self.snapshot = self.controller.rename_scene(name, scene_id=current.id)
                elif action == 'duplicate':
                    self.snapshot = self.controller.duplicate_scene(name)
                else:
                    self.snapshot = self.controller.create_scene(name)
            self._section = '工作场景'
            self._configuring_scene = scene_id is None and action != 'delete'
            self._status_text = ''
            self._show_editor = False; self._editing = None; self._render_expanded()
        except (ValueError, OSError) as exc: self._error(exc)

    def _begin_add(self):
        self._editing = None; self._show_editor = True; self._render_expanded()

    def _begin_edit(self, item):
        self._editing = item; self._show_editor = True; self._render_expanded()

    def _save_editor(self, draft):
        if self._editing is None: self.snapshot = self.controller.add_resource(draft)
        else: self.snapshot = self.controller.edit_resource(self._editing.id, draft)
        self._editing = None; self._show_editor = False; self._render_expanded()

    def _error(self, exc):
        messagebox.showerror('操作未完成', str(exc), parent=self)

    def _set_status(self, text):
        self._status_text = text
        if self.is_expanded and hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.configure(text=text)

    def _open_link(self, item):
        self._dispatch((item,))

    def _open_link_in_browser(self, item, browser):
        self._dispatch((BrowserOpenItem(**asdict(item), browser=browser),))

    def _dispatch(self, items, scene_name=None):
        try:
            batch = self.dispatcher.submit(items)
            name = scene_name if scene_name is not None else items[0].name
            self._batch_context[batch] = [name, len(items), []]
            self._set_status(f'正在打开“{name}”…')
        except ValueError as exc: self._error(exc)

    def _launch_scene(self, scene):
        if scene.items:
            self._dispatch(scene.items, scene_name=scene.name)
        else:
            self._set_status('没有可打开的项目。右键场景方块，选择“编辑场景”添加。')

    def _poll_results(self):
        for result in self.dispatcher.poll():
            context = self._batch_context.get(result.batch_id)
            if context is None: continue
            context[2].append(result)
            if len(context[2]) == context[1]:
                self._batch_context.pop(result.batch_id)
                details = '\n'.join(f'{r.name}：{r.message}' for r in context[2])
                failures = sum(r.status != 'requested' for r in context[2])
                self._set_status(f'“{context[0]}”：已发出 {context[1] - failures} 项请求，失败/超时 {failures} 项。')
                if failures:
                    messagebox.showinfo(f'启动结果 · {context[0]}', details, parent=self)

    def start_desktop_services(self):
        if self._tray is not None: return
        from .tray import TrayIcon
        self._tray = TrayIcon(self._commands, name=APP_ID, title='工作场景 · 单击显示',
                              show_label='显示工作场景', image=build_scene_icon(64))
        self._tray.start(); self.after(100, self._desktop_tick)

    def _desktop_tick(self):
        self._poll_results()
        super()._desktop_tick()

    def report_callback_exception(self, exc, value, tb):
        report_scene_error(value.with_traceback(tb), parent=self, root=self.controller.store.root)

    def destroy(self):
        if self._closed: return
        self._closed = True
        self.dispatcher.close()
        super().destroy()


def build_scenes_app(store, startup, dispatcher=None):
    controller = SceneController(store); controller.initialize()
    return ScenesWindow(controller, startup, dispatcher)
