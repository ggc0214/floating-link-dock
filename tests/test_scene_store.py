from dataclasses import replace
import json
import pytest
from floating_link_dock.scene_store import SceneStore


def legacy(tmp_path):
    old = tmp_path / 'old'; old.mkdir()
    (old / 'links.json').write_text(json.dumps({'version': 1, 'links': [
        {'id': 'old', 'name': '旧网址', 'url': 'https://example.com', 'order': 0, 'x': 17, 'y': 29}]}), encoding='utf-8')
    (old / 'settings.json').write_text(json.dumps({'version': 1, 'settings': {'launch_at_startup': True, 'x': 100}}), encoding='utf-8')
    return old


def test_import_is_read_only_and_once(tmp_path):
    old = legacy(tmp_path); before = {p.name: p.read_bytes() for p in old.iterdir()}
    store = SceneStore(tmp_path / 'new', old)
    assert store.needs_initialization()
    candidate, settings, warnings = store.legacy_candidate()
    assert candidate.items[0].x == 17 and not settings.launch_at_startup
    assert not (tmp_path / 'new').exists()
    doc = store.initialize(True)
    assert doc.active_scene.items[0].name == '旧网址'
    assert doc.active_scene.items[0].target == 'https://example.com'
    store.save(replace(doc, scenes=(replace(doc.active_scene, items=()),)))
    assert not store.needs_initialization()
    assert store.initialize(True).active_scene.items == ()
    assert {p.name: p.read_bytes() for p in old.iterdir()} == before


def test_cancel_and_damaged_new_file_do_not_reimport(tmp_path):
    old = legacy(tmp_path); store = SceneStore(tmp_path / 'new', old)
    assert store.initialize(False).active_scene.items == ()
    store.path.write_text('broken', encoding='utf-8')
    doc, warnings = store.load()
    assert warnings and not doc.active_scene.items
    assert list((store.root / 'backups').glob('*.json'))
    assert store.initialize(True).active_scene.items == ()


def test_invalid_legacy_is_not_modified(tmp_path):
    old = legacy(tmp_path); (old / 'links.json').write_bytes(b'broken')
    store = SceneStore(tmp_path / 'new', old)
    doc = store.initialize(True)
    assert doc.active_scene.items == ()
    assert (old / 'links.json').read_bytes() == b'broken'
    assert sorted(p.name for p in old.iterdir()) == ['links.json', 'settings.json']


@pytest.mark.parametrize('change', ['duplicate', 'boolean', 'active'])
def test_bad_document_recovery(tmp_path, change):
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    raw = json.loads(store.path.read_text(encoding='utf-8'))
    if change == 'duplicate': raw['scenes'].append(raw['scenes'][0])
    if change == 'boolean': raw['settings']['x'] = True
    if change == 'active': raw['active_scene_id'] = 'missing'
    store.path.write_text(json.dumps(raw), encoding='utf-8')
    doc, warnings = store.load()
    assert warnings and len(doc.scenes) == 1
