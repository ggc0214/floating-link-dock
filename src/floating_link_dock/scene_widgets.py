import sys
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from . import theme
from .scene_models import ResourceDraft, validate_resource
from .tile_board import TileBoard
from .platform_integration import installed_browsers

# The existing folder kind can store either path without assuming a file extension.
KINDS = {'网址': 'url', '文件 / 文件夹': 'folder', '应用': 'app'}
BADGES = {'url': '网', 'file': '路径', 'folder': '路径', 'app': '应用'}


class SceneBoard(TileBoard):
    def __init__(self, master, scenes, *, on_open, on_edit, on_position, on_manage):
        super().__init__(master, scenes, on_open=on_open, on_edit=on_edit,
                         on_delete=None, on_position=on_position, font_family=theme.SCENE_FONT)
        self._on_manage = on_manage
        for _, tile, scene in self._items.values():
            badge, title = tile.winfo_children()
            badge.configure(text=f'{len(scene.items)} 项', width=46, font=(theme.SCENE_FONT, 11, 'bold'))
            if len(scene.name) > 12:
                title.configure(text=f'{scene.name[:11]}…')
        if not scenes:
            ctk.CTkLabel(self.canvas, text='还没有工作场景\n点击右上角“＋ 场景”创建',
                         font=(theme.SCENE_FONT, 13), text_color=theme.TEXT_MUTED).place(
                             relx=.5, rely=.4, anchor='center')

    def _menu(self, key, event):
        scene = self._items[key][2]
        menu = tk.Menu(self, tearoff=False, font=(theme.SCENE_FONT, 11))
        menu.add_command(label=scene.name, state='disabled')
        menu.add_command(label='编辑场景', command=lambda: self._on_edit(scene))
        menu.add_command(label='重命名场景', command=lambda: self._on_manage('rename', key))
        menu.add_separator()
        menu.add_command(label='删除场景', command=lambda: self._on_manage('delete', key))
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()


class ResourceEditor(ctk.CTkFrame):
    def __init__(self, master, *, item, on_save, on_cancel, in_scene=False):
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        self._on_save = on_save
        self._auto_open = item.auto_open if item else in_scene
        self.grid_columnconfigure(0, weight=1)
        self.kind_menu = ctk.CTkOptionMenu(self, values=list(KINDS), command=self._kind_changed,
                                          font=(theme.SCENE_FONT, 13), dropdown_font=(theme.SCENE_FONT, 13),
                                          fg_color=theme.ACCENT, button_color=theme.BORDER, text_color=theme.TEXT)
        self.kind_menu.grid(row=0, column=0, padx=12, pady=(12, 6), sticky='ew')
        kind = item.kind if item else 'url'
        self.kind_menu.set(next(label for label, value in KINDS.items() if value == ('folder' if kind == 'file' else kind)))
        self.name_entry = ctk.CTkEntry(self, placeholder_text='名称', text_color=theme.TEXT,
                                       font=(theme.SCENE_FONT, 13))
        self.name_entry.grid(row=1, column=0, sticky='ew', padx=12, pady=6)
        self.hint = ctk.CTkLabel(self, text='', anchor='w', font=(theme.SCENE_FONT, 11), text_color=theme.TEXT_MUTED)
        self.hint.grid(row=2, column=0, padx=12, sticky='ew')
        self.target_entry = ctk.CTkTextbox(self, height=95, wrap='word', fg_color=theme.BACKGROUND,
                                           text_color=theme.TEXT, font=(theme.SCENE_FONT, 13))
        self.target_entry.grid(row=3, column=0, sticky='ew', padx=12, pady=4)
        pickers = ctk.CTkFrame(self, fg_color='transparent')
        pickers.grid(row=4, column=0, padx=12, pady=4, sticky='ew')
        pickers.grid_columnconfigure((0, 1), weight=1)
        self.browse_buttons = []
        for col, (label, chooser) in enumerate([('选择文件', filedialog.askopenfilename),
                                                ('选择文件夹', filedialog.askdirectory)]):
            button = ctk.CTkButton(pickers, text=label, height=28, width=90,
                                   font=(theme.SCENE_FONT, 13),
                                   command=lambda select=chooser: self._browse(select),
                                   fg_color=theme.SURFACE_RAISED, text_color=theme.TEXT)
            button.grid(row=0, column=col, padx=2, sticky='ew')
            self.browse_buttons.append(button)
        self.error_label = ctk.CTkLabel(self, text='', text_color=theme.DANGER, wraplength=290, font=(theme.SCENE_FONT, 11))
        self.error_label.grid(row=5, column=0, padx=12)
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=6, column=0, padx=12, pady=(4, 12), sticky='e')
        for col, (title, command) in enumerate([('取消', on_cancel), ('保存', self._submit)]):
            ctk.CTkButton(actions, text=title, command=command, width=72, height=28,
                          font=(theme.SCENE_FONT, 13),
                          fg_color=theme.ACCENT, text_color=theme.TEXT).grid(row=0, column=col, padx=3)
        if item:
            self.name_entry.insert(0, item.name)
            self.target_entry.insert('1.0', item.target)
        self._kind_changed(self.kind_menu.get())

    def _kind_changed(self, label):
        kind = KINDS[label]
        self.hint.configure(text={'url': '粘贴网页、飞书多维表或云文档链接',
                                   'folder': '粘贴完整路径，打开时自动识别文件或文件夹',
                                   'app': ('选择 .app 应用，也可粘贴完整路径' if sys.platform == 'darwin'
                                           else '选择 .exe、.lnk 或 .bat，也可粘贴路径')}[kind])
        file_button, folder_button = self.browse_buttons
        file_button.configure(text='选择应用' if kind == 'app' else '选择文件',
                              state='normal' if kind in {'folder', 'app'} else 'disabled')
        folder_button.configure(state='normal' if kind == 'folder' else 'disabled')

    def _browse(self, chooser):
        if KINDS[self.kind_menu.get()] == 'app':
            if sys.platform == 'darwin':
                from AppKit import NSModalResponseOK, NSOpenPanel
                panel = NSOpenPanel.openPanel()
                panel.setTitle_('选择应用')
                panel.setAllowedFileTypes_(['app'])
                panel.setTreatsFilePackagesAsDirectories_(False)
                value = panel.URL().path() if panel.runModal() == NSModalResponseOK else ''
            else:
                value = chooser(parent=self, title='选择应用',
                                filetypes=[('应用、快捷方式和批处理', ('*.exe', '*.lnk', '*.bat'))])
        else:
            value = chooser(parent=self, title='选择共享目录或本地目标')
        if value:
            self.target_entry.delete('1.0', 'end'); self.target_entry.insert('1.0', value)

    def _submit(self):
        try:
            draft = validate_resource(ResourceDraft(KINDS[self.kind_menu.get()], self.name_entry.get(),
                        self.target_entry.get('1.0', 'end-1c'), self._auto_open))
            self._on_save(draft)
        except (ValueError, OSError) as exc:
            self.error_label.configure(text=str(exc))


class ResourceBoard(TileBoard):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, font_family=theme.SCENE_FONT, **kwargs)
        for _, tile, item in self._items.values():
            tile.winfo_children()[0].configure(text=BADGES[item.kind])

    def _menu(self, key, event):
        item = self._items[key][2]
        menu = tk.Menu(self, tearoff=False, font=(theme.SCENE_FONT, 11), bg=theme.SURFACE, fg=theme.TEXT,
                       activebackground=theme.SURFACE_HOVER)
        menu.add_command(label=item.name, state='disabled')
        menu.add_command(label='打开', command=lambda: self._on_open(item))
        if item.kind == 'url' and self._on_open_browser is not None:
            for browser in installed_browsers():
                menu.add_command(label=f'使用 {browser.name} 打开',
                                 command=lambda b=browser: self._on_open_browser(item, b))
        menu.add_separator()
        menu.add_command(label='编辑', command=lambda: self._on_edit(item))
        menu.add_command(label='删除', command=lambda: self._on_delete(item))
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()
