"""Pure scene data and validation: no filesystem/network calls here."""
from dataclasses import dataclass, field, replace
import ntpath
import re
from uuid import uuid4

from .link_service import normalize_url
from .models import AppSettings

FILE_TYPES = {'.pdf', '.xlsx', '.xls', '.xlsm', '.docx', '.doc', '.pptx', '.ppt',
              '.txt', '.csv', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.psd', '.ai'}


@dataclass(frozen=True)
class ResourceDraft:
    kind: str
    name: str
    target: str
    auto_open: bool = False


@dataclass(frozen=True)
class ResourceItem:
    id: str
    kind: str
    name: str
    target: str
    order: int
    x: int | None = None
    y: int | None = None
    auto_open: bool = False

    @property
    def url(self):
        return self.target if self.kind == 'url' else ''


@dataclass(frozen=True)
class Scene:
    id: str
    name: str
    items: tuple[ResourceItem, ...] = ()
    x: int | None = None
    y: int | None = None


@dataclass(frozen=True)
class SceneDocument:
    scenes: tuple[Scene, ...]
    active_scene_id: str
    settings: AppSettings = field(default_factory=AppSettings)
    initialized: bool = True

    @property
    def active_scene(self):
        return next(s for s in self.scenes if s.id == self.active_scene_id)


def empty_document():
    scene = Scene(str(uuid4()), '常用网址')
    return SceneDocument((scene,), scene.id)


def validate_scene_name(name, existing_names):
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 40:
        raise ValueError('场景名称须为1至40个字符')
    if cleaned.casefold() in {n.casefold() for n in existing_names}:
        raise ValueError('场景名称不能重复')
    return cleaned


def validate_windows_path(target):
    # Reject ambiguous Win32 namespaces, ADS and names Win32 silently rewrites.
    if any(ord(c) < 32 for c in target) or any(c in target for c in '<>"|?*'):
        raise ValueError('路径包含不支持的字符')
    value = target.strip().replace('/', '\\')
    if value.startswith(('\\\\?\\', '\\\\.\\')):
        raise ValueError('不支持设备路径')
    drive, tail = ntpath.splitdrive(value)
    unc = drive.startswith('\\\\') and len(drive[2:].split('\\')) == 2
    if not ((re.fullmatch('[A-Za-z]:', drive) and tail.startswith('\\')) or unc):
        raise ValueError('请选择完整盘符路径或 NAS 共享路径')
    if ':' in tail or (unc and ':' in drive) or any(
        part in ('.', '..') or part.endswith(('.', ' '))
        or part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
        for part in tail.split('\\') if part
    ):
        raise ValueError('路径包含不安全或不明确的名称')
    return value


def validate_resource(draft):
    if draft.kind not in {'url', 'file', 'folder', 'app'}:
        raise ValueError('不支持的项目类型')
    name = draft.name.strip()
    if not name or len(name) > 80:
        raise ValueError('请填写1至80个字符的名称')
    if not isinstance(draft.auto_open, bool):
        raise ValueError('自动打开设置无效')
    target = draft.target
    if draft.kind == 'url':
        target = normalize_url(target)
    else:
        if draft.kind == 'app':
            target = target.strip()
            if len(target) >= 2 and target[0] == target[-1] == '"':
                target = target[1:-1]
        target = validate_windows_path(target)
        if draft.kind == 'app' and (target.startswith('\\\\') or ntpath.splitext(target)[1].lower() not in {'.exe', '.lnk', '.bat'}):
            raise ValueError('请选择盘符下的 .exe 程序、.lnk 快捷方式或 .bat 批处理')
        if draft.kind == 'file' and ntpath.splitext(target)[1].lower() not in FILE_TYPES:
            raise ValueError('暂不支持此文件类型；请使用日常文档或图片，不支持程序、脚本和快捷方式')
    return replace(draft, name=name, target=target)
