"""Independent scenes store. Legacy reading never invokes legacy recovery writes."""
from dataclasses import asdict, fields, replace
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from .models import AppSettings
from .scene_models import (ResourceDraft, ResourceItem, Scene, SceneDocument,
                           empty_document, validate_resource, validate_scene_name)
from .storage import JsonStore
from .tile_layout import next_tile_position


def _settings(raw, importing=False):
    if not isinstance(raw, dict): raise ValueError('设置格式无效')
    values = {}
    for field in fields(AppSettings):
        if field.name in raw:
            value = raw[field.name]
            if field.name in ('x', 'y'):
                if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                    raise ValueError('坐标格式无效')
            elif not isinstance(value, bool): raise ValueError('设置类型无效')
            values[field.name] = value
    if importing: values['launch_at_startup'] = False
    return AppSettings(**values)


class SceneStore:
    def __init__(self, root=None, legacy_root=None):
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
        self.root = Path(root) if root is not None else base / 'FloatingLinkDockScenes'
        self.legacy_root = Path(legacy_root) if legacy_root is not None else base / 'FloatingLinkDock'
        if self.root.absolute() == self.legacy_root.absolute():
            raise ValueError('场景版与原版不能使用相同数据目录')
        self.path = self.root / 'scenes.json'
        self.warnings = ()

    def needs_initialization(self):
        return not self.path.exists()

    def legacy_candidate(self):
        doc = empty_document(); settings = AppSettings(); warnings = []
        try:
            path = self.legacy_root / 'links.json'
            if path.exists():
                raw = json.loads(path.read_text(encoding='utf-8'))
                if raw.get('version') != 1 or not isinstance(raw.get('links'), list):
                    raise ValueError('旧网址格式不支持')
                links = [JsonStore._parse_link(item) for item in raw['links']]
                links.sort(key=lambda item: item.order)
                if len({i.id for i in links}) != len(links): raise ValueError('旧网址ID重复')
                items = []
                for i, link in enumerate(links):
                    draft = validate_resource(ResourceDraft('url', link.name, link.url))
                    x, y = (link.x, link.y) if link.x is not None and link.y is not None else next_tile_position(items)
                    items.append(ResourceItem(link.id, 'url', draft.name, draft.target, i, x, y))
                doc = replace(doc, scenes=(replace(doc.active_scene, items=tuple(items)),))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            warnings.append('原版网址无法读取，未修改原文件；已准备空场景。')
        try:
            path = self.legacy_root / 'settings.json'
            if path.exists():
                raw = json.loads(path.read_text(encoding='utf-8'))
                if raw.get('version') != 1: raise ValueError('旧设置格式不支持')
                settings = _settings(raw['settings'], importing=True)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            warnings.append('原版设置无法读取，使用场景版默认设置。')
        return doc.active_scene, settings, tuple(warnings)

    def initialize(self, import_legacy):
        if not self.needs_initialization(): return self.load()[0]
        doc = empty_document()
        if import_legacy:
            scene, settings, self.warnings = self.legacy_candidate()
            doc = SceneDocument((scene,), scene.id, settings)
        self.save(doc)
        return doc

    def load(self):
        if self.needs_initialization():
            return self.initialize(False), self.warnings
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            doc = self._parse(raw)
            return doc, self.warnings
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            backup = self.root / 'backups' / f'scenes-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, backup)
            doc = empty_document()
            self.save(doc)
            self.warnings = ('场景数据损坏，已在场景版目录备份并建立空场景；没有重新导入或修改原版。',)
            return doc, self.warnings

    @staticmethod
    def _parse(raw):
        if raw['version'] != 2 or raw['initialized'] is not True: raise ValueError('场景版本无效')
        if not isinstance(raw['scenes'], list) or not raw['scenes']: raise ValueError('至少保留一个场景')
        scenes = []; ids = set(); names = []
        for scene_raw in raw['scenes']:
            sid = scene_raw['id']
            if not isinstance(sid, str) or not sid or sid in ids: raise ValueError('场景ID无效')
            ids.add(sid)
            name = validate_scene_name(scene_raw['name'], names); names.append(name)
            if not isinstance(scene_raw['items'], list): raise ValueError('资源列表无效')
            items = []
            for item_raw in scene_raw['items']:
                # Older builds allowed text tiles in both tabs.
                if item_raw.get('kind') == 'text':
                    continue
                item = ResourceItem(**item_raw)
                if not isinstance(item.id, str) or not item.id or item.id in ids: raise ValueError('资源ID无效')
                ids.add(item.id)
                draft = validate_resource(ResourceDraft(item.kind, item.name, item.target, item.auto_open))
                for value in (item.order, item.x, item.y):
                    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                        raise ValueError('资源顺序或坐标无效')
                if item.order is None: raise ValueError('顺序不能为空')
                x, y = (item.x, item.y) if item.x is not None and item.y is not None else next_tile_position(items)
                items.append(replace(item, name=draft.name, target=draft.target, auto_open=draft.auto_open, x=x, y=y))
            x, y = scene_raw.get('x'), scene_raw.get('y')
            for value in (x, y):
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError('场景坐标无效')
            items.sort(key=lambda item: item.order)
            if len(items) < len(scene_raw['items']):
                items = [replace(item, order=index) for index, item in enumerate(items)]
            scenes.append(Scene(sid, name, tuple(items), x, y))
        if raw['active_scene_id'] not in {s.id for s in scenes}: raise ValueError('当前场景无效')
        placed = [s for s in scenes if s.x is not None and s.y is not None]
        for index, scene in enumerate(scenes):
            if scene.name != '常用网址' and (scene.x is None or scene.y is None):
                x, y = next_tile_position(placed)
                scenes[index] = replace(scene, x=x, y=y)
                placed.append(scenes[index])
        return SceneDocument(tuple(scenes), raw['active_scene_id'], _settings(raw['settings']))

    def save(self, document):
        payload = {'version': 2, **asdict(document)}
        # JSON round-trip also validates immutable tuple serialization before publishing.
        self._parse(json.loads(json.dumps(payload, ensure_ascii=False)))
        self.root.mkdir(parents=True, exist_ok=True)
        # Older scene builds cannot read application entries.
        before_apps = self.root / 'backups' / 'before-app-entries.json'
        if (self.path.exists() and not before_apps.exists()
                and any(item.kind == 'app' for scene in document.scenes for item in scene.items)):
            before_apps.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, before_apps)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path); temporary = None
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
