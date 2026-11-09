from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from tkinter import messagebox
from typing import Protocol
from queue import SimpleQueue, Empty
import time
import sys

import customtkinter as ctk

from . import theme
from .face_icon import build_face_icon
from .app_controller import AppController
from .geometry import (Point, Rect, choose_expansion, clamp_window, is_drag,
                       snap_to_edge, half_hidden_origin)
from .models import Link, LinkDraft
from .storage import JsonStore
from .widgets import InlineLinkEditor, LinkRow
from .tile_board import TileBoard
from .platform_integration import (
    IntegrationError,
    StartupManager,
    get_cursor_work_area,
    get_work_area_for_point,
    open_in_default_browser,
    open_in_browser,
    system_reduces_motion,
)


class StartupPort(Protocol):
    def is_enabled(self) -> bool: ...

    def set_enabled(self, enabled: bool) -> None: ...


class FloatingDockWindow(ctk.CTk):
    _floating_color = theme.ACCENT
    _floating_hover = theme.ACCENT_HOVER
    _floating_border = theme.BORDER

    def _build_mark(self):
        return build_face_icon()

    def __init__(self, controller: AppController, startup: StartupPort) -> None:
        ctk.set_appearance_mode("light")
        super().__init__(fg_color=theme.BACKGROUND)
        self.controller = controller
        self.startup = startup
        self.snapshot = controller.snapshot
        self.is_expanded = False
        self._editing: Link | None = None
        self._show_editor = False
        self._drag_start: Point | None = None
        self._window_start: Point | None = None
        self._dragged = False
        self._hidden = False
        self._outside_since = None
        self._tray = None
        self._commands = SimpleQueue()
        self._collapsed_origin = Point(
            self.snapshot.settings.x if self.snapshot.settings.x is not None else 32,
            self.snapshot.settings.y if self.snapshot.settings.y is not None else 120,
        )
        self._reduced_motion = system_reduces_motion()
        face = self._build_mark()
        self._button_face = ctk.CTkImage(light_image=face, dark_image=face, size=(32, 32))
        self._header_face = ctk.CTkImage(light_image=face, dark_image=face, size=(26, 26))

        self.title("Floating Link Dock")
        self.minsize(theme.COLLAPSED_SIZE, theme.COLLAPSED_SIZE)
        if sys.platform == 'darwin':
            # Keep the managed Aqua window eligible for keyboard focus.
            self.attributes('-stylemask', ())
        else:
            self.overrideredirect(True)
        # Keep the desktop dock out of the taskbar; the tray remains its entry point.
        if sys.platform == 'win32':
            self.attributes("-toolwindow", True)
        self.attributes("-topmost", self.snapshot.settings.always_on_top)
        self.configure(fg_color=theme.BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        if sys.platform == 'darwin':
            self.tk.createcommand('::tk::mac::ReopenApplication', self._mac_reopen)
        self._render_collapsed()
        self.after(50, self._show_warnings)
        self.after(100, self._onboard)
        if hasattr(self.startup, 'configuration_warning'):
            warning = self.startup.configuration_warning()
            if warning:
                self.after(150, lambda: messagebox.showwarning('开机启动', warning, parent=self))

    def _onboard(self) -> None:
        self.show_panel()
        if not self.snapshot.settings.onboarding_complete:
            self.snapshot = self.controller.update_settings(onboarding_complete=True)

    def _mac_reopen(self, *_args) -> None:
        self._commands.put('show')

    def start_desktop_services(self) -> None:
        if self._tray is not None:
            return
        from .tray import TrayIcon
        self._tray = TrayIcon(self._commands)
        self._tray.start()
        self.after(100, self._desktop_tick)

    def _desktop_tick(self) -> None:
        try:
            while True:
                command = self._commands.get_nowait()
                if command == "quit":
                    self.destroy()
                    return
                if command == "reset":
                    self.reset_position()
                elif command == "show":
                    self.show_panel()
        except Empty:
            pass
        self._check_edge_hide()
        self.after(100, self._desktop_tick)

    def _position(self, origin: Point) -> None:
        tk.Tk.geometry(self, f"+{origin.x}+{origin.y}")

    def _reveal(self) -> None:
        if self._hidden:
            self._position(self._collapsed_origin)
            self._hidden = False
        self._outside_since = None

    def _check_edge_hide(self) -> None:
        if self.is_expanded or self._drag_start is not None:
            return
        if not self.snapshot.settings.edge_auto_hide:
            self._reveal()
            return
        x, y = self.winfo_pointerxy()
        inside = (self.winfo_x() <= x < self.winfo_x() + self.winfo_width()
                  and self.winfo_y() <= y < self.winfo_y() + self.winfo_height())
        if inside:
            self._reveal()
            return
        if self._outside_since is None:
            self._outside_since = time.monotonic()
        if not self._hidden and time.monotonic() - self._outside_since >= 0.7:
            hidden = half_hidden_origin(
                self._collapsed_origin, (self.winfo_width(), self.winfo_height()),
                self._work_area(self._collapsed_origin),
            )
            if hidden != self._collapsed_origin:
                self._position(hidden)
                self._hidden = True

    def show_panel(self) -> None:
        self._reveal()
        self.deiconify()
        self.update_idletasks()
        if not self.is_expanded:
            self.toggle_expanded()
        self.lift()

    def reset_position(self) -> None:
        area = self._work_area()
        self._collapsed_origin = Point(area.left + 32, area.top + 120)
        self._hidden = False
        self.snapshot = self.controller.update_settings(
            x=self._collapsed_origin.x, y=self._collapsed_origin.y)
        self._render_collapsed()
        self.show_panel()

    def report_callback_exception(self, exc, value, tb) -> None:
        from .errors import report_error
        report_error(value.with_traceback(tb), parent=self)

    def destroy(self) -> None:
        if self._tray is not None:
            self._tray.stop()
            self._tray = None
        super().destroy()

    def _work_area(self, point: Point | None = None) -> Rect:
        try:
            if point is not None:
                return get_work_area_for_point(point)
            return get_cursor_work_area()
        except IntegrationError:
            return Rect(0, 0, self.winfo_screenwidth(), self.winfo_screenheight())

    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _render_collapsed(self) -> None:
        self._clear()
        self.is_expanded = False
        self._hidden = False
        self._outside_since = None
        origin = snap_to_edge(
            self._collapsed_origin,
            (round(self._apply_window_scaling(theme.COLLAPSED_SIZE)),
             round(self._apply_window_scaling(theme.COLLAPSED_SIZE))),
            self._work_area(self._collapsed_origin),
        )
        self._collapsed_origin = origin
        self.geometry(
            f"{theme.COLLAPSED_SIZE}x{theme.COLLAPSED_SIZE}+{origin.x}+{origin.y}"
        )
        button = ctk.CTkButton(
            self,
            text="",
            image=self._button_face,
            border_spacing=0,
            width=theme.COLLAPSED_SIZE,
            height=theme.COLLAPSED_SIZE,
            corner_radius=10,
            fg_color=self._floating_color,
            hover_color=self._floating_hover,
            text_color=theme.TEXT,
            border_width=2,
            border_color=self._floating_border,
            font=("Segoe UI Symbol", 30, "bold"),
        )
        button.pack(fill="both", expand=True)
        button.bind("<ButtonPress-1>", self._drag_press)
        button.bind("<B1-Motion>", self._drag_motion)
        button.bind("<ButtonRelease-1>", self._drag_release)
        self._bind_context_menu(button)

    def _render_expanded(self) -> None:
        self._clear()
        self.is_expanded = True
        self.configure(fg_color=theme.BACKGROUND)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent", height=62)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        header.grid_columnconfigure(1, weight=1)
        grip = ctk.CTkLabel(
            header,
            text="",
            image=self._header_face,
            width=38,
            height=38,
            corner_radius=11,
            fg_color=theme.ACCENT,
            text_color=theme.TEXT,
            font=("Segoe UI Symbol", 25, "bold"),
        )
        grip.grid(row=0, column=0, padx=(0, 10))
        title = ctk.CTkLabel(
            header,
            text="常用网址",
            anchor="w",
            text_color=theme.TEXT,
            font=(theme.FONT, 17, "bold"),
        )
        title.grid(row=0, column=1, sticky="w")
        add = ctk.CTkButton(
            header,
            text="＋ 添加",
            width=74,
            height=32,
            corner_radius=10,
            fg_color=theme.SURFACE_RAISED,
            hover_color=theme.SURFACE_HOVER,
            text_color=theme.TEXT,
            border_width=2,
            border_color=theme.BORDER,
            command=self._begin_add,
        )
        add.grid(row=0, column=2, padx=(4, 6))
        collapse = ctk.CTkButton(
            header,
            text="−",
            width=32,
            height=32,
            corner_radius=10,
            fg_color="transparent",
            hover_color=theme.SURFACE_HOVER,
            text_color=theme.TEXT_MUTED,
            command=self.toggle_expanded,
        )
        collapse.grid(row=0, column=3)
        for widget in (header, grip, title):
            widget.bind("<ButtonPress-1>", self._drag_press)
            widget.bind("<B1-Motion>", self._drag_motion_expanded)
            widget.bind("<ButtonRelease-1>",
                        self._drag_release_grip if widget is grip
                        else self._drag_release_expanded)
            self._bind_context_menu(widget)

        if self._show_editor:
            editor = InlineLinkEditor(
                self,
                link=self._editing,
                on_save=self._save_editor,
                on_cancel=self._cancel_editor,
            )
            editor.grid(row=1, column=0, sticky="new", padx=14, pady=8)
            return

        self.board = TileBoard(
            self, self.snapshot.links, on_open=self._open_link,
            on_edit=self._begin_edit, on_delete=self._delete_link,
            on_position=self._position_link,
            on_open_browser=self._open_link_in_browser,
        )
        self.board.grid(row=1, column=0, sticky="nsew", padx=(12, 8), pady=(0, 12))
        if not self.snapshot.links:
            empty = ctk.CTkFrame(self.board.canvas, fg_color=theme.BACKGROUND)
            empty.place(relx=0.5, rely=0.4, anchor="center")
            ctk.CTkLabel(
                empty,
                text="还没有常用网址",
                text_color=theme.TEXT,
                font=(theme.FONT, 15, "bold"),
            ).pack(pady=(0, 5))
            ctk.CTkLabel(
                empty,
                text="添加第一个网址，之后从这里一键打开",
                text_color=theme.TEXT_MUTED,
                font=(theme.FONT, 11),
            ).pack(pady=(0, 14))
            ctk.CTkButton(
                empty,
                text="添加网址",
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_HOVER,
                text_color=theme.BACKGROUND,
                command=self._begin_add,
            ).pack()

    def _position_link(self, link_id: str, x: int, y: int) -> None:
        self.snapshot = self.controller.position_link(link_id, x, y)

    def toggle_expanded(self) -> None:
        self._reveal()
        if self.is_expanded:
            self._show_editor = False
            self._editing = None
            self._render_collapsed()
            return
        anchor = Rect(
            self.winfo_x(),
            self.winfo_y(),
            self.winfo_x() + self.winfo_width(),
            self.winfo_y() + self.winfo_height(),
        )
        self._collapsed_origin = Point(anchor.left, anchor.top)
        placement = choose_expansion(
            anchor,
            (round(self._apply_window_scaling(theme.PANEL_WIDTH)),
             round(self._apply_window_scaling(theme.PANEL_HEIGHT))),
            self._work_area(Point(anchor.left, anchor.top)),
        )
        self.geometry(
            f"{theme.PANEL_WIDTH}x{theme.PANEL_HEIGHT}+{placement.origin.x}+{placement.origin.y}"
        )
        if not self._reduced_motion:
            self.attributes("-alpha", 0.92)
            self.after(80, lambda: self.attributes("-alpha", 1.0))
        self._render_expanded()

    def _drag_press(self, event) -> None:
        self._reveal()
        self._drag_start = Point(event.x_root, event.y_root)
        self._window_start = Point(self.winfo_x(), self.winfo_y())
        self._dragged = False

    def _drag_motion(self, event) -> None:
        if self._drag_start is None or self._window_start is None:
            return
        current = Point(event.x_root, event.y_root)
        self._dragged = is_drag(self._drag_start, current)
        if self._dragged:
            x = self._window_start.x + current.x - self._drag_start.x
            y = self._window_start.y + current.y - self._drag_start.y
            self.geometry(f"+{x}+{y}")

    def _drag_release(self, event) -> None:
        if self._drag_start is None:
            return
        current = Point(event.x_root, event.y_root)
        dragged = self._dragged or is_drag(self._drag_start, current)
        self._drag_start = None
        if dragged:
            origin = snap_to_edge(
                Point(self.winfo_x(), self.winfo_y()),
                (self.winfo_width(), self.winfo_height()),
                self._work_area(Point(self.winfo_x(), self.winfo_y())),
            )
            self._collapsed_origin = origin
            self._position(origin)
            self.snapshot = self.controller.update_settings(x=origin.x, y=origin.y)
        else:
            self.toggle_expanded()

    def _drag_motion_expanded(self, event) -> None:
        self._drag_motion(event)

    def _drag_release_grip(self, event) -> None:
        if self._drag_start is None:
            return
        dragged = self._dragged or is_drag(
            self._drag_start, Point(event.x_root, event.y_root)
        )
        self._dragged = dragged
        self._drag_release_expanded(event)
        if not dragged:
            self.toggle_expanded()

    def _drag_release_expanded(self, _event) -> None:
        if self._dragged:
            self._collapsed_origin = clamp_window(
                Point(self.winfo_x(), self.winfo_y()),
                (theme.COLLAPSED_SIZE, theme.COLLAPSED_SIZE),
                self._work_area(Point(self.winfo_x(), self.winfo_y())),
            )
            self.snapshot = self.controller.update_settings(
                x=self._collapsed_origin.x, y=self._collapsed_origin.y
            )
        self._drag_start = None

    def _begin_add(self) -> None:
        self._editing = None
        self._show_editor = True
        self._render_expanded()

    def _begin_edit(self, link: Link) -> None:
        self._editing = link
        self._show_editor = True
        self._render_expanded()

    def _cancel_editor(self) -> None:
        self._editing = None
        self._show_editor = False
        self._render_expanded()

    def _save_editor(self, draft: LinkDraft) -> None:
        try:
            if self._editing is None:
                self.snapshot = self.controller.add_link(draft)
            else:
                self.snapshot = self.controller.edit_link(self._editing.id, draft)
        except OSError as exc:
            messagebox.showerror("保存失败", f"网址没有更改。\n{exc}", parent=self)
            return
        self._editing = None
        self._show_editor = False
        self._render_expanded()

    def _delete_link(self, link: Link) -> None:
        if not messagebox.askyesno(
            "删除网址", f"确定删除“{link.name}”吗？", parent=self
        ):
            return
        try:
            self.snapshot = self.controller.delete_link(link.id)
        except OSError as exc:
            messagebox.showerror("删除失败", f"网址仍然保留。\n{exc}", parent=self)
        self._render_expanded()

    def _move_link(self, link: Link, direction: int) -> None:
        try:
            self.snapshot = self.controller.move_link(link.id, direction)  # type: ignore[arg-type]
        except OSError as exc:
            messagebox.showerror("排序失败", f"顺序没有更改。\n{exc}", parent=self)
        self._render_expanded()

    def _open_link(self, link: Link) -> None:
        try:
            open_in_default_browser(link.url)
        except IntegrationError as exc:
            messagebox.showerror("无法打开网站", str(exc), parent=self)

    def _open_link_in_browser(self, link: Link, browser) -> None:
        try:
            open_in_browser(link.url, browser)
        except IntegrationError as exc:
            messagebox.showerror("无法打开网站", str(exc), parent=self)

    def _show_context_menu(self, event) -> None:
        self._drag_start = None
        self._dragged = False
        self._reveal()
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=theme.SURFACE,
            fg=theme.TEXT,
            activebackground=theme.SURFACE_HOVER,
            activeforeground=theme.TEXT,
        )
        top_var = tk.BooleanVar(value=self.snapshot.settings.always_on_top)
        startup_var = tk.BooleanVar(value=self.startup.is_enabled())
        menu.add_checkbutton(
            label="保持置顶", variable=top_var, command=lambda: self._set_topmost(top_var.get())
        )
        menu.add_checkbutton(
            label="开机启动",
            variable=startup_var,
            command=lambda: self._set_startup(startup_var.get()),
        )
        menu.add_separator()
        hide_var = tk.BooleanVar(value=self.snapshot.settings.edge_auto_hide)
        menu.add_checkbutton(label="贴边半隐藏", variable=hide_var,
                             command=lambda: self._set_edge_hide(hide_var.get()))
        menu.add_command(label="重置位置", command=self.reset_position)
        menu.add_separator()
        menu.add_command(label="退出", command=self.destroy)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return 'break'

    def _bind_context_menu(self, widget) -> None:
        for sequence in (('<Button-2>', '<Button-3>', '<Control-Button-1>')
                         if sys.platform == 'darwin' else ('<Button-3>',)):
            widget.bind(sequence, self._show_context_menu)

    def _set_edge_hide(self, enabled: bool) -> None:
        self.snapshot = self.controller.update_settings(edge_auto_hide=enabled)
        self._reveal()

    def _set_topmost(self, enabled: bool) -> None:
        try:
            self.snapshot = self.controller.update_settings(always_on_top=enabled)
            self.attributes("-topmost", enabled)
        except OSError as exc:
            messagebox.showerror("设置失败", str(exc), parent=self)

    def _set_startup(self, enabled: bool) -> None:
        previous = self.snapshot.settings.launch_at_startup
        try:
            self.startup.set_enabled(enabled)
            self.snapshot = self.controller.update_settings(launch_at_startup=enabled)
        except (IntegrationError, OSError) as exc:
            try:
                self.startup.set_enabled(previous)
            except IntegrationError:
                pass
            messagebox.showerror("设置失败", str(exc), parent=self)

    def _show_warnings(self) -> None:
        if self.snapshot.warnings:
            messagebox.showwarning(
                "数据已恢复", "\n".join(self.snapshot.warnings), parent=self
            )


def build_app(store: JsonStore, startup: StartupPort) -> FloatingDockWindow:
    controller = AppController(store)
    controller.initialize()
    return FloatingDockWindow(controller, startup)
