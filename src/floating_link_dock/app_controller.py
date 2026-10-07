from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol, Sequence

from .link_service import create_link, reorder_links
from .models import AppSettings, Link, LinkDraft
from .storage import LoadResult, seed_links
from .tile_layout import next_tile_position


class Store(Protocol):
    def load_links(self) -> LoadResult[list[Link]]: ...

    def save_links(self, links: Sequence[Link]) -> None: ...

    def load_settings(self) -> LoadResult[AppSettings]: ...

    def save_settings(self, settings: AppSettings) -> None: ...


@dataclass(frozen=True, slots=True)
class AppSnapshot:
    links: tuple[Link, ...]
    settings: AppSettings
    warnings: tuple[str, ...] = ()


class AppController:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._snapshot: AppSnapshot | None = None

    @property
    def snapshot(self) -> AppSnapshot:
        if self._snapshot is None:
            raise RuntimeError("controller is not initialized")
        return self._snapshot

    def initialize(self) -> AppSnapshot:
        links_result = self._store.load_links()
        settings_result = self._store.load_settings()
        links = list(links_result.value)
        settings = settings_result.value

        if not links_result.existed and not settings.first_run_complete:
            links = seed_links()
            self._store.save_links(links)
            settings = replace(settings, first_run_complete=True)
            self._store.save_settings(settings)

        positioned = [link for link in links if link.x is not None and link.y is not None]
        migrated = False
        for index, link in enumerate(links):
            if link.x is None or link.y is None:
                x, y = next_tile_position(positioned)
                links[index] = replace(link, x=x, y=y)
                positioned.append(links[index])
                migrated = True
        if migrated:
            self._store.save_links(links)

        warnings = tuple(
            warning
            for warning in (links_result.warning, settings_result.warning)
            if warning
        )
        self._snapshot = AppSnapshot(tuple(links), settings, warnings)
        return self._snapshot

    def add_link(self, draft: LinkDraft) -> AppSnapshot:
        x, y = next_tile_position(list(self.snapshot.links))
        candidate = [*self.snapshot.links,
                     replace(create_link(draft, len(self.snapshot.links)), x=x, y=y)]
        return self._publish_links(candidate)

    def position_link(self, link_id: str, x: int, y: int) -> AppSnapshot:
        if x < 0 or y < 0:
            raise ValueError("tile position must not be negative")
        if not any(link.id == link_id for link in self.snapshot.links):
            raise KeyError(link_id)
        return self._publish_links([
            replace(link, x=x, y=y) if link.id == link_id else link
            for link in self.snapshot.links
        ])

    def edit_link(self, link_id: str, draft: LinkDraft) -> AppSnapshot:
        candidate = [
            replace(link, name=draft.name, url=draft.url)
            if link.id == link_id
            else link
            for link in self.snapshot.links
        ]
        if not any(link.id == link_id for link in self.snapshot.links):
            raise KeyError(link_id)
        return self._publish_links(candidate)

    def delete_link(self, link_id: str) -> AppSnapshot:
        remaining = [link for link in self.snapshot.links if link.id != link_id]
        if len(remaining) == len(self.snapshot.links):
            raise KeyError(link_id)
        candidate = [replace(link, order=index) for index, link in enumerate(remaining)]
        return self._publish_links(candidate)

    def move_link(self, link_id: str, direction: Literal[-1, 1]) -> AppSnapshot:
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or 1")
        source = next(
            (index for index, link in enumerate(self.snapshot.links) if link.id == link_id),
            None,
        )
        if source is None:
            raise KeyError(link_id)
        target = source + direction
        if not 0 <= target < len(self.snapshot.links):
            return self.snapshot
        candidate = reorder_links(list(self.snapshot.links), source, target)
        return self._publish_links(candidate)

    def update_settings(self, **changes: object) -> AppSnapshot:
        settings = replace(self.snapshot.settings, **changes)
        self._store.save_settings(settings)
        self._snapshot = replace(self.snapshot, settings=settings)
        return self._snapshot

    def _publish_links(self, candidate: Sequence[Link]) -> AppSnapshot:
        self._store.save_links(candidate)
        self._snapshot = replace(self.snapshot, links=tuple(candidate))
        return self._snapshot
