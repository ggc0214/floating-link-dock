"""A freely positioned, scrollable website tile canvas."""
import tkinter as tk
import sys

import customtkinter as ctk

from . import theme
from .geometry import Point, is_drag
from .tile_layout import TILE_SIZE, TILE_MARGIN
from .platform_integration import installed_browsers


class TileBoard(ctk.CTkFrame):
    def __init__(self, master, links, *, on_open, on_edit, on_delete, on_position,
                 on_open_browser=None, font_family=theme.FONT):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background=theme.BACKGROUND,
                                highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ctk.CTkScrollbar(self, command=self.canvas.yview,
                                     button_color=theme.ACCENT,
                                     button_hover_color=theme.BORDER)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self._scale = self._get_widget_scaling()
        self._on_open, self._on_edit = on_open, on_edit
        self._on_delete, self._on_position = on_delete, on_position
        self._on_open_browser = on_open_browser
        self._items = {}
        self._positions = {}
        self._drag_start = None
        self._active = None
        self._dragged = False
        self._content_height = 1
        for index, link in enumerate(links):
            tile = ctk.CTkFrame(self.canvas, width=TILE_SIZE, height=TILE_SIZE,
                               fg_color=theme.TILE_COLORS[index % len(theme.TILE_COLORS)],
                               corner_radius=16, border_width=2,
                               border_color=theme.BORDER)
            tile.grid_propagate(False)
            tile.pack_propagate(False)
            icon = ctk.CTkLabel(tile, text=link.name[:1].upper(), width=28, height=28,
                                corner_radius=10, fg_color=theme.SURFACE,
                                text_color=theme.TEXT, font=(font_family, 14, "bold"))
            icon.pack(pady=(10, 2))
            title = ctk.CTkLabel(tile, text=link.name, width=70, height=28,
                                 wraplength=68, text_color=theme.TEXT,
                                 font=(font_family, 10, "bold"))
            title.pack(pady=(0, 6))
            x, y = link.x or 0, link.y or 0
            item = self.canvas.create_window(x * self._scale, y * self._scale,
                                            window=tile, anchor="nw")
            self._items[link.id] = (item, tile, link)
            self._positions[link.id] = Point(x, y)
            for widget in (tile, icon, title):
                widget.bind("<ButtonPress-1>", lambda event, key=link.id: self._press(key, event))
                widget.bind("<B1-Motion>", self._motion)
                widget.bind("<ButtonRelease-1>", self._release)
                for sequence in (('<Button-2>', '<Button-3>', '<Control-Button-1>')
                                 if sys.platform == 'darwin' else ('<Button-3>',)):
                    widget.bind(sequence, lambda event, key=link.id: self._context_click(key, event))
                widget.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Configure>", self._resize)
        self.canvas.bind("<MouseWheel>", self._wheel)

    def _resize(self, _event=None):
        width = self.canvas.winfo_width()
        size = TILE_SIZE * self._scale
        for key, position in self._positions.items():
            x = min(position.x * self._scale, max(0, width - size))
            self.canvas.coords(self._items[key][0], x, position.y * self._scale)
        bottom = max((p.y + TILE_SIZE + TILE_MARGIN for p in self._positions.values()), default=0)
        self._content_height = max(self.canvas.winfo_height(), bottom * self._scale)
        self.canvas.configure(scrollregion=(0, 0, width, self._content_height))

    def _wheel(self, event):
        delta = event.delta if sys.platform == 'darwin' else event.delta / 120
        self.canvas.yview_scroll(-int(delta), "units")
        return "break"

    def _press(self, key, event):
        self._active = key
        self._drag_start = Point(event.x_root, event.y_root)
        self._start_coords = tuple(self.canvas.coords(self._items[key][0]))
        self._dragged = False
        self.canvas.tag_raise(self._items[key][0])
        self._items[key][1].lift()

    def _motion(self, event):
        if self._active is None:
            return
        current = Point(event.x_root, event.y_root)
        self._dragged = self._dragged or is_drag(self._drag_start, current)
        if not self._dragged:
            return
        size = TILE_SIZE * self._scale
        x = self._start_coords[0] + current.x - self._drag_start.x
        y = self._start_coords[1] + current.y - self._drag_start.y
        x = min(max(0, x), max(0, self.canvas.winfo_width() - size))
        y = min(max(0, y), max(0, self._content_height - size))
        self.canvas.coords(self._items[self._active][0], x, y)

    def _release(self, event):
        if self._active is None:
            return
        key = self._active
        self._motion(event)
        self._active = None
        if self._dragged:
            x, y = self.canvas.coords(self._items[key][0])
            try:
                self._on_position(key, round(x / self._scale), round(y / self._scale))
            except OSError:
                self.canvas.coords(self._items[key][0], *self._start_coords)
                raise
            self._positions[key] = Point(round(x / self._scale), round(y / self._scale))
            self._resize()
        else:
            self._on_open(self._items[key][2])

    def _menu(self, key, event):
        link = self._items[key][2]
        menu = tk.Menu(self, tearoff=False, bg=theme.SURFACE, fg=theme.TEXT,
                       activebackground=theme.SURFACE_HOVER, activeforeground=theme.TEXT)
        menu.add_command(label=link.name, state="disabled")
        menu.add_command(label="使用默认浏览器打开", command=lambda: self._on_open(link))
        if self._on_open_browser is not None:
            for browser in installed_browsers():
                menu.add_command(label=f"使用 {browser.name} 打开",
                                 command=lambda selected=browser: self._on_open_browser(link, selected))
        menu.add_separator()
        menu.add_command(label="编辑", command=lambda: self._on_edit(link))
        menu.add_command(label="删除", command=lambda: self._on_delete(link))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _context_click(self, key, event):
        self._active = None
        self._drag_start = None
        self._menu(key, event)
        return 'break'
