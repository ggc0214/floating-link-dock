"""A freely positioned, scrollable website tile canvas."""
import tkinter as tk
from urllib.parse import urlparse

import customtkinter as ctk

from . import theme
from .geometry import Point, is_drag
from .tile_layout import TILE_SIZE, TILE_MARGIN


class TileBoard(ctk.CTkFrame):
    def __init__(self, master, links, *, on_open, on_edit, on_delete, on_position):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background=theme.BACKGROUND,
                                highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ctk.CTkScrollbar(self, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self._scale = self._get_widget_scaling()
        self._on_open, self._on_edit = on_open, on_edit
        self._on_delete, self._on_position = on_delete, on_position
        self._items = {}
        self._positions = {}
        self._drag_start = None
        self._active = None
        self._dragged = False
        self._content_height = 1
        for link in links:
            tile = ctk.CTkFrame(self.canvas, width=TILE_SIZE, height=TILE_SIZE,
                               fg_color=theme.SURFACE, corner_radius=14)
            tile.grid_propagate(False)
            tile.pack_propagate(False)
            icon = ctk.CTkLabel(tile, text=link.name[:1].upper(), width=32, height=32,
                                corner_radius=10, fg_color=theme.SURFACE_RAISED,
                                text_color=theme.ACCENT, font=(theme.FONT, 16, "bold"))
            icon.pack(pady=(10, 2))
            title = ctk.CTkLabel(tile, text=link.name, width=84, height=32,
                                 wraplength=80, text_color=theme.TEXT,
                                 font=(theme.FONT, 11, "bold"))
            title.pack()
            host = (urlparse(link.url).hostname or "").removeprefix("www.")
            domain = ctk.CTkLabel(tile, text=host if len(host) < 16 else host[:13] + "…",
                                  width=84, height=14, text_color=theme.TEXT_MUTED,
                                  font=(theme.FONT, 9))
            domain.pack()
            x, y = link.x or 0, link.y or 0
            item = self.canvas.create_window(x * self._scale, y * self._scale,
                                            window=tile, anchor="nw")
            self._items[link.id] = (item, tile, link)
            self._positions[link.id] = Point(x, y)
            for widget in (tile, icon, title, domain):
                widget.bind("<ButtonPress-1>", lambda event, key=link.id: self._press(key, event))
                widget.bind("<B1-Motion>", self._motion)
                widget.bind("<ButtonRelease-1>", self._release)
                widget.bind("<Button-3>", lambda event, key=link.id: self._menu(key, event))
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
        self.canvas.yview_scroll(-int(event.delta / 120), "units")
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
        menu.add_command(label="打开网站", command=lambda: self._on_open(link))
        menu.add_command(label="编辑", command=lambda: self._on_edit(link))
        menu.add_command(label="删除", command=lambda: self._on_delete(link))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
