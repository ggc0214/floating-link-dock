from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

import customtkinter as ctk

from . import theme
from .link_service import LinkValidationError, validate_link
from .models import Link, LinkDraft


class LinkRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        link: Link,
        *,
        on_open: Callable[[Link], None],
        on_edit: Callable[[Link], None],
        on_delete: Callable[[Link], None],
        on_move: Callable[[Link, int], None],
        can_move_up: bool,
        can_move_down: bool,
    ) -> None:
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=theme.RADIUS)
        self.link = link
        self.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkLabel(
            self,
            text=(link.name[:1] or "↗").upper(),
            width=34,
            height=34,
            corner_radius=10,
            fg_color=theme.SURFACE_RAISED,
            text_color=theme.ACCENT,
            font=(theme.FONT, 14, "bold"),
        )
        icon.grid(row=0, column=0, rowspan=2, padx=(10, 9), pady=9)

        name = ctk.CTkLabel(
            self,
            text=link.name,
            anchor="w",
            text_color=theme.TEXT,
            font=(theme.FONT, 13, "bold"),
        )
        name.grid(row=0, column=1, sticky="sew", pady=(8, 0))
        domain = urlparse(link.url).hostname or link.url
        host = ctk.CTkLabel(
            self,
            text=domain.removeprefix("www."),
            anchor="w",
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT, 10),
        )
        host.grid(row=1, column=1, sticky="new", pady=(0, 8))

        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=8)
        buttons = [
            ("↑", lambda: on_move(link, -1), can_move_up),
            ("↓", lambda: on_move(link, 1), can_move_down),
            ("✎", lambda: on_edit(link), True),
            ("×", lambda: on_delete(link), True),
        ]
        for index, (label, command, enabled) in enumerate(buttons):
            button = ctk.CTkButton(
                self.actions,
                text=label,
                width=26,
                height=26,
                corner_radius=8,
                fg_color="transparent",
                hover_color=theme.SURFACE_RAISED,
                text_color=theme.DANGER if label == "×" else theme.TEXT_MUTED,
                command=command,
                state="normal" if enabled else "disabled",
                font=(theme.FONT, 12, "bold"),
            )
            button.grid(row=0, column=index, padx=1)

        for widget in (self, icon, name, host):
            widget.bind("<Button-1>", lambda _event, item=link: on_open(item))
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _enter(self, _event=None) -> None:
        self.configure(fg_color=theme.SURFACE_HOVER)

    def _leave(self, _event=None) -> None:
        self.configure(fg_color=theme.SURFACE)


class InlineLinkEditor(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        link: Link | None,
        on_save: Callable[[LinkDraft], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.SURFACE,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=theme.RADIUS,
        )
        self._on_save = on_save
        self.grid_columnconfigure(0, weight=1)

        self.name_entry = ctk.CTkEntry(
            self,
            placeholder_text="网站名称（可留空）",
            height=36,
            corner_radius=10,
            border_color=theme.BORDER,
            fg_color=theme.BACKGROUND,
            text_color=theme.TEXT,
        )
        self.name_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="例如 example.com",
            height=36,
            corner_radius=10,
            border_color=theme.BORDER,
            fg_color=theme.BACKGROUND,
            text_color=theme.TEXT,
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        if link is not None:
            self.name_entry.insert(0, link.name)
            self.url_entry.insert(0, link.url)

        self.error_label = ctk.CTkLabel(
            self, text="", anchor="w", text_color=theme.DANGER, font=(theme.FONT, 10)
        )
        self.error_label.grid(row=2, column=0, sticky="ew", padx=12)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="e", padx=10, pady=(4, 10))
        ctk.CTkButton(
            actions,
            text="取消",
            width=62,
            height=30,
            fg_color="transparent",
            hover_color=theme.SURFACE_RAISED,
            text_color=theme.TEXT_MUTED,
            command=on_cancel,
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="保存",
            width=66,
            height=30,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BACKGROUND,
            command=self._submit,
        ).grid(row=0, column=1)
        self.url_entry.bind("<Return>", lambda _event: self._submit())
        self.url_entry.focus_set()

    def _submit(self) -> None:
        try:
            draft = validate_link(self.name_entry.get(), self.url_entry.get())
        except LinkValidationError as exc:
            self.error_label.configure(text=str(exc))
            return
        self._on_save(draft)
