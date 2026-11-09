"""Controller transaction coverage, separated from store tests per plan."""
import pytest
from floating_link_dock.scene_store import SceneStore
from floating_link_dock.scene_controller import SceneController
from floating_link_dock.scene_models import ResourceDraft


def test_controller_scene_transactions_and_write_failure(tmp_path, monkeypatch):
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    c = SceneController(store); c.initialize()
    original = c.snapshot.document.active_scene_id
    c.add_resource(ResourceDraft('text', '话术', 'hello'))
    first = c.snapshot.links[0]
    c.duplicate_scene('复制')
    assert c.snapshot.links[0].id != first.id
    copied_id = c.snapshot.document.active_scene_id
    c.position_link(c.snapshot.links[0].id, 55, 65)
    c.select_scene(original)
    assert c.snapshot.links[0].x == 8
    before = c.snapshot
    monkeypatch.setattr(store, 'save', lambda doc: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError): c.create_scene('失败')
    assert c.snapshot == before
    monkeypatch.undo()
    c.delete_scene(copied_id)
    with pytest.raises(ValueError): c.delete_scene(original)
    c.rename_scene('重命名')
    assert store.load()[0].active_scene.name == '重命名'
