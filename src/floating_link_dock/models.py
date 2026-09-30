from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Link:
    id: str
    name: str
    url: str
    order: int


@dataclass(frozen=True, slots=True)
class LinkDraft:
    name: str
    url: str


@dataclass(slots=True)
class AppSettings:
    x: int | None = None
    y: int | None = None
    always_on_top: bool = True
    launch_at_startup: bool = False
    first_run_complete: bool = False
