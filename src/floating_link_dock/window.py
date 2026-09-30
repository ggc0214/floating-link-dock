from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from tkinter import messagebox
from typing import Protocol

import customtkinter as ctk

from . import theme
from .app_controller import AppController
from .geometry import Point, Rect, choose_expansion, clamp_window, is_drag
from .models import Link, LinkDraft
from .storage import JsonStore
from .widgets import InlineLinkEditor, LinkRow
from .windows_integration import (
    IntegrationError,
    StartupManager,
    get_cursor_work_area,
    get_work_area_for_point,
    open_in_default_browser,
    system_reduces_motion,
)


class StartupPort(Protocol):
    def is_enabled(self) -> bool: ...

    def set_enabled(self, enabled: bool) -> None: ...


class FloatingDockWindow(ctk.CTk):
    def __init__(self, controller: AppController, startup: StartupPort) -> None:
        ctk.set_appearance_mode("dark")
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
        self._collapsed_origin = Point(
            self.snapshot.settings.x if self.snapshot.settings.x is not None else 32,
            self.snapshot.settings.y if self.snapshot.settings.y is not None else 120,
        )
        self._reduced_motion = system_reduces_motion()

        self.title("Floating Link Dock")
        self.overrideredirect(True)
        self.attributes("-topmost", self.snapshot.settings.always_on_top)
        self.configure(fg_color=theme.BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._render_collapsed()
        self.after(50, self._show_warnings)

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
        origin = clamp_window(
            self._collapsed_origin,
            (theme.COLLAPSED_SIZE, theme.COLLAPSED_SIZE),
            self._work_area(self._collapsed_origin),
        )
        self._collapsed_origin = origin
        self.geometry(
            f"{theme.COLLAPSED_SIZE}x{theme.COLLAPSED_SIZE}+{origin.x}+{origin.y}"
        )
        button = ctk.CTkButton(
            self,
            text="↗",
            width=theme.COLLAPSED_SIZE,
            height=theme.COLLAPSED_SIZE,
            corner_radius=theme.RADIUS,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BACKGROUND,
            font=(theme.FONT, 22, "bold"),
        )
        button.pack(fill="both", expand=True)
        button.bind("<ButtonPress-1>", self._drag_press)
        button.bind("<B1-Motion>", self._drag_motion)
        button.bind("<ButtonRelease-1>", self._drag_release)
        button.bind("<Button-3>", self._show_context_menu)

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
            text="↗",
            width=38,
            height=38,
            corner_radius=11,
            fg_color=theme.ACCENT,
            text_color=theme.BACKGROUND,
            font=(theme.FONT, 18, "bold"),
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
            text_color=theme.ACCENT,
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
            widget.bind("<ButtonRelease-1>", self._drag_release_expanded)
            widget.bind("<Button-3>", self._show_context_menu)

        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=theme.SURFACE_RAISED,
            scrollbar_button_hover_color=theme.ACCENT,
        )
        content.grid(row=1, column=0, sticky="nsew", padx=(12, 8), pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)

        row = 0
        if self._show_editor:
            editor = InlineLinkEditor(
                content,
                link=self._editing,
                on_save=self._save_editor,
                on_cancel=self._cancel_editor,
            )
            editor.grid(row=row, column=0, sticky="ew", padx=(0, 4), pady=(0, 8))
            row += 1

        if not self.snapshot.links:
            empty = ctk.CTkFrame(content, fg_color="transparent")
            empty.grid(row=row, column=0, sticky="ew", padx=18, pady=60)
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
        else:
            for index, link in enumerate(self.snapshot.links):
                item = LinkRow(
                    content,
                    link,
                    on_open=self._open_link,
                    on_edit=self._begin_edit,
                    on_delete=self._delete_link,
                    on_move=self._move_link,
                    can_move_up=index > 0,
                    can_move_down=index < len(self.snapshot.links) - 1,
                )
                item.grid(row=row, column=0, sticky="ew", padx=(0, 4), pady=4)
                row += 1

    def toggle_expanded(self) -> None:
        if self.is_expanded:
            self._show_editor = False
            self._editing = None
            self._render_collapsed()
            return
        anchor = Rect(
            self.winfo_x(),
            self.winfo_y(),
            self.winfo_x() + theme.COLLAPSED_SIZE,
            self.winfo_y() + theme.COLLAPSED_SIZE,
        )
        self._collapsed_origin = Point(anchor.left, anchor.top)
        placement = choose_expansion(
            anchor,
            (theme.PANEL_WIDTH, theme.PANEL_HEIGHT),
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
            origin = clamp_window(
                Point(self.winfo_x(), self.winfo_y()),
                (theme.COLLAPSED_SIZE, theme.COLLAPSED_SIZE),
                self._work_area(Point(self.winfo_x(), self.winfo_y())),
            )
            self._collapsed_origin = origin
            self.geometry(f"+{origin.x}+{origin.y}")
            self.snapshot = self.controller.update_settings(x=origin.x, y=origin.y)
        else:
            self.toggle_expanded()

    def _drag_motion_expanded(self, event) -> None:
        self._drag_motion(event)

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

    def _show_context_menu(self, event) -> None:
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
        menu.add_command(label="退出", command=self.destroy)
        menu.tk_popup(event.x_root, event.y_root)

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
