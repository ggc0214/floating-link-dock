from __future__ import annotations

from dataclasses import replace

import pytest

import floating_link_dock.window as window_module
from floating_link_dock.app_controller import AppController
from floating_link_dock.geometry import Point, Rect
from floating_link_dock.models import AppSettings, Link, LinkDraft
from floating_link_dock.storage import LoadResult, seed_links


class FakeStore:
    def __init__(
        self,
        links: list[Link] | None = None,
        *,
        links_existed: bool = True,
        settings: AppSettings | None = None,
        link_warning: str | None = None,
    ) -> None:
        self.links = list(links or [])
        self.links_existed = links_existed
        self.settings = settings or AppSettings()
        self.link_warning = link_warning
        self.fail_next_save = False

    def load_links(self) -> LoadResult[list[Link]]:
        return LoadResult(list(self.links), self.links_existed, self.link_warning)

    def save_links(self, links: list[Link] | tuple[Link, ...]) -> None:
        if self.fail_next_save:
            self.fail_next_save = False
            raise OSError("disk full")
        self.links = list(links)
        self.links_existed = True

    def load_settings(self) -> LoadResult[AppSettings]:
        return LoadResult(replace(self.settings), True)

    def save_settings(self, settings: AppSettings) -> None:
        self.settings = replace(settings)


def test_first_run_seeds_three_links() -> None:
    store = FakeStore(links_existed=False, settings=AppSettings(first_run_complete=False))

    snapshot = AppController(store).initialize()

    assert len(snapshot.links) == 3
    assert [link.name for link in snapshot.links] == [link.name for link in seed_links()]
    assert store.settings.first_run_complete is True


def test_existing_empty_list_stays_empty() -> None:
    store = FakeStore([], links_existed=True, settings=AppSettings(first_run_complete=True))

    snapshot = AppController(store).initialize()

    assert snapshot.links == ()


def test_add_edit_delete_and_reorder_persist_before_render() -> None:
    original = Link("a", "A", "https://a.example", 0)
    controller = AppController(FakeStore([original]))
    controller.initialize()

    added = controller.add_link(LinkDraft("B", "https://b.example"))
    added_id = added.links[1].id
    edited = controller.edit_link(added_id, LinkDraft("Bee", "https://bee.example"))
    moved = controller.move_link(added_id, -1)
    deleted = controller.delete_link("a")

    assert [link.name for link in added.links] == ["A", "B"]
    assert edited.links[1].name == "Bee"
    assert [link.id for link in moved.links] == [added_id, "a"]
    assert [(link.id, link.order) for link in deleted.links] == [(added_id, 0)]


def test_failed_save_keeps_previous_snapshot() -> None:
    store = FakeStore([Link("a", "A", "https://a.example", 0)])
    controller = AppController(store)
    before = controller.initialize()
    store.fail_next_save = True

    with pytest.raises(OSError, match="disk full"):
        controller.add_link(LinkDraft("B", "https://b.example"))

    assert controller.snapshot == before


def test_corrupt_data_warning_is_exposed_in_snapshot() -> None:
    store = FakeStore([], links_existed=True, link_warning="已恢复损坏数据")

    snapshot = AppController(store).initialize()

    assert snapshot.warnings == ("已恢复损坏数据",)


class FakeStartupManager:
    def __init__(self) -> None:
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


def test_build_app_creates_collapsed_window_and_can_expand() -> None:
    from floating_link_dock.window import build_app

    store = FakeStore(
        [Link("a", "A", "https://a.example", 0)],
        settings=AppSettings(x=100, y=100, first_run_complete=True),
    )
    app = build_app(store, FakeStartupManager())
    try:
        app.update_idletasks()
        assert app.is_expanded is False
        assert app.title() == "Floating Link Dock"
        app.toggle_expanded()
        app.update_idletasks()
        assert app.is_expanded is True
    finally:
        app.destroy()


def test_saved_position_uses_its_own_monitor_work_area(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[Point] = []
    monkeypatch.setattr(
        window_module,
        "get_work_area_for_point",
        lambda point: requested.append(point) or Rect(1920, 0, 3840, 1040),
        raising=False,
    )
    store = FakeStore(
        [Link("a", "A", "https://a.example", 0)],
        settings=AppSettings(x=2100, y=100, first_run_complete=True),
    )

    app = window_module.build_app(store, FakeStartupManager())
    try:
        app.update_idletasks()
        assert requested[0] == Point(2100, 100)
        assert app._collapsed_origin == Point(2100, 100)
    finally:
        app.destroy()
