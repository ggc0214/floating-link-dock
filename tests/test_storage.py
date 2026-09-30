from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from floating_link_dock.models import AppSettings, Link
from floating_link_dock.storage import JsonStore, StoragePaths, seed_links


def make_store(tmp_path: Path) -> JsonStore:
    return JsonStore(StoragePaths.for_user(tmp_path))


def test_paths_live_under_local_app_data(tmp_path: Path) -> None:
    paths = StoragePaths.for_user(tmp_path)

    assert paths.root == tmp_path / "FloatingLinkDock"
    assert paths.links_file == paths.root / "links.json"
    assert paths.settings_file == paths.root / "settings.json"
    assert paths.backups_dir == paths.root / "backups"


def test_links_round_trip(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    links = [Link("a", "A", "https://a.example", 0)]

    store.save_links(links)
    result = store.load_links()

    assert result.value == links
    assert result.existed is True
    assert result.warning is None
    assert json.loads(store.paths.links_file.read_text("utf-8"))["version"] == 1


def test_settings_round_trip(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    settings = AppSettings(100, 200, False, True, True)

    store.save_settings(settings)

    assert store.load_settings().value == settings


def test_seed_links_are_created_only_for_missing_first_run_data(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    missing = store.load_links()
    store.save_links([])
    existing_empty = store.load_links()

    assert missing.existed is False
    assert existing_empty.existed is True
    assert len(seed_links()) == 3
    assert [item.order for item in seed_links()] == [0, 1, 2]


@pytest.mark.parametrize(
    "payload",
    [
        '{"version": 1, "links": [',
        '{"version": 99, "links": []}',
        '{"version": 1, "links": [{"id": "a"}]}',
    ],
)
def test_invalid_link_files_are_backed_up(tmp_path: Path, payload: str) -> None:
    store = make_store(tmp_path)
    store.paths.root.mkdir(parents=True)
    store.paths.links_file.write_text(payload, encoding="utf-8")

    result = store.load_links()

    assert result.value == []
    assert result.existed is True
    assert result.warning is not None
    backups = list(store.paths.backups_dir.glob("links-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text("utf-8") == payload


def test_atomic_replace_failure_keeps_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = make_store(tmp_path)
    original = [Link("a", "A", "https://a.example", 0)]
    store.save_links(original)

    def fail_replace(source: str | Path, target: str | Path) -> None:
        raise OSError("replace blocked")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace blocked"):
        store.save_links([Link("b", "B", "https://b.example", 0)])

    assert json.loads(store.paths.links_file.read_text("utf-8"))["links"][0]["id"] == "a"
    assert not list(store.paths.root.glob("*.tmp"))


def test_failed_save_does_not_mutate_callers_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = make_store(tmp_path)
    links = [Link("a", "A", "https://a.example", 9)]
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("no")))

    with pytest.raises(OSError):
        store.save_links(links)

    assert links == [Link("a", "A", "https://a.example", 9)]
