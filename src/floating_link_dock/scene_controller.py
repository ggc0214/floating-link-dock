from dataclasses import dataclass, replace
from uuid import uuid4
from .scene_models import ResourceItem, Scene, validate_resource, validate_scene_name
from .tile_layout import next_tile_position


@dataclass(frozen=True)
class SceneSnapshot:
    document: object
    warnings: tuple[str, ...] = ()

    @property
    def links(self): return self.document.active_scene.items
    @property
    def settings(self): return self.document.settings


class SceneController:
    def __init__(self, store):
        self.store = store
        self.snapshot = None

    def initialize(self):
        document, warnings = self.store.load()
        self.snapshot = SceneSnapshot(document, warnings)
        return self.snapshot

    def _publish(self, document):
        self.store.save(document)
        self.snapshot = replace(self.snapshot, document=document)
        return self.snapshot

    def ensure_common_scene(self):
        """Pin a common entry collection without reclassifying existing scenes."""
        doc = self.snapshot.document
        existing = next((s for s in doc.scenes if s.name == '常用网址'), None)
        if existing is not None: return existing.id
        common = Scene(str(uuid4()), '常用网址')
        self._publish(replace(doc, scenes=(*doc.scenes, common)))
        return common.id

    def _publish_items(self, items):
        doc = self.snapshot.document
        scene = replace(doc.active_scene, items=tuple(items))
        return self._publish(replace(doc, scenes=tuple(scene if s.id == scene.id else s for s in doc.scenes)))

    def create_scene(self, name):
        doc = self.snapshot.document
        x, y = next_tile_position(doc.scenes)
        scene = Scene(str(uuid4()), validate_scene_name(name, [s.name for s in doc.scenes]), x=x, y=y)
        return self._publish(replace(doc, scenes=(*doc.scenes, scene), active_scene_id=scene.id))

    def rename_scene(self, name, *, scene_id=None):
        doc = self.snapshot.document
        target_id = doc.active_scene_id if scene_id is None else scene_id
        if not any(s.id == target_id for s in doc.scenes):
            raise ValueError('找不到要重命名的场景')
        name = validate_scene_name(name, [s.name for s in doc.scenes if s.id != target_id])
        scenes = tuple(replace(s, name=name) if s.id == target_id else s for s in doc.scenes)
        return self._publish(replace(doc, scenes=scenes))

    def duplicate_scene(self, name):
        doc = self.snapshot.document
        name = validate_scene_name(name, [s.name for s in doc.scenes])
        items = tuple(replace(i, id=str(uuid4())) for i in doc.active_scene.items)
        x, y = next_tile_position(doc.scenes)
        scene = Scene(str(uuid4()), name, items, x, y)
        return self._publish(replace(doc, scenes=(*doc.scenes, scene), active_scene_id=scene.id))

    def delete_scene(self, scene_id, *, fallback_scene_id=None):
        doc = self.snapshot.document
        if len(doc.scenes) == 1: raise ValueError('至少保留一个场景')
        remaining = tuple(s for s in doc.scenes if s.id != scene_id)
        if len(remaining) == len(doc.scenes): raise KeyError(scene_id)
        if fallback_scene_id is not None and fallback_scene_id not in {s.id for s in remaining}:
            raise ValueError('后续场景不存在')
        active = (fallback_scene_id or remaining[0].id) if scene_id == doc.active_scene_id else doc.active_scene_id
        return self._publish(replace(doc, scenes=remaining, active_scene_id=active))

    def select_scene(self, scene_id):
        doc = self.snapshot.document
        if scene_id not in {s.id for s in doc.scenes}: raise KeyError(scene_id)
        return self._publish(replace(doc, active_scene_id=scene_id))

    def position_scene(self, scene_id, x, y):
        doc = self.snapshot.document
        if not any(s.id == scene_id for s in doc.scenes):
            raise KeyError(scene_id)
        scenes = tuple(replace(s, x=x, y=y) if s.id == scene_id else s for s in doc.scenes)
        return self._publish(replace(doc, scenes=scenes))

    def add_resource(self, draft):
        draft = validate_resource(draft)
        items = self.snapshot.links
        x, y = next_tile_position(items)
        item = ResourceItem(str(uuid4()), draft.kind, draft.name, draft.target, len(items), x, y, draft.auto_open)
        return self._publish_items((*items, item))

    def edit_resource(self, item_id, draft):
        draft = validate_resource(draft)
        if not any(i.id == item_id for i in self.snapshot.links): raise KeyError(item_id)
        return self._publish_items(replace(i, kind=draft.kind, name=draft.name, target=draft.target, auto_open=draft.auto_open)
                                   if i.id == item_id else i for i in self.snapshot.links)

    def delete_link(self, item_id):
        items = tuple(i for i in self.snapshot.links if i.id != item_id)
        if len(items) == len(self.snapshot.links): raise KeyError(item_id)
        return self._publish_items(replace(i, order=n) for n, i in enumerate(items))

    def position_link(self, item_id, x, y):
        if x < 0 or y < 0: raise ValueError('坐标不能为负')
        if not any(i.id == item_id for i in self.snapshot.links): raise KeyError(item_id)
        return self._publish_items(replace(i, x=x, y=y) if i.id == item_id else i for i in self.snapshot.links)

    def update_settings(self, **changes):
        doc = self.snapshot.document
        return self._publish(replace(doc, settings=replace(doc.settings, **changes)))
