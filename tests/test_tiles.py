from floating_link_dock.app_controller import AppController
from floating_link_dock.models import Link, LinkDraft
from floating_link_dock.storage import JsonStore, StoragePaths
from floating_link_dock.tile_layout import next_tile_position
from test_app_smoke import FakeStore
import pytest


def test_existing_urls_migrate_without_losing_ids_or_names():
    links = [Link("a", "A", "https://a.example", 0),
             Link("b", "B", "https://b.example", 1)]
    store = FakeStore(links)
    controller = AppController(store)
    snapshot = controller.initialize()
    assert [(x.id, x.url) for x in snapshot.links] == [(x.id, x.url) for x in links]
    assert [(x.x, x.y) for x in snapshot.links] == [(8, 8), (116, 8)]
    assert controller.initialize().links == snapshot.links


def test_drag_position_survives_edit_and_restart(tmp_path):
    store = JsonStore(StoragePaths.for_user(tmp_path))
    controller = AppController(store)
    initial = controller.initialize()
    key = initial.links[0].id
    controller.position_link(key, 47, 180)
    controller.edit_link(key, LinkDraft("Changed", "https://changed.example"))
    restarted = AppController(store).initialize()
    link = next(x for x in restarted.links if x.id == key)
    assert (link.x, link.y, link.name) == (47, 180, "Changed")


def test_failed_position_save_keeps_last_saved_layout():
    store = FakeStore([Link("a", "A", "https://a.example", 0, 8, 8)])
    controller = AppController(store)
    before = controller.initialize()
    store.fail_next_save = True
    with pytest.raises(OSError):
        controller.position_link("a", 30, 100)
    assert controller.snapshot == before


def test_new_tile_avoids_freely_positioned_tiles():
    assert next_tile_position([Link("a", "A", "https://a.example", 0, 40, 20)]) == (224, 8)
