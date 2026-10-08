from __future__ import annotations

import json
import os
import sys
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Generic, Sequence, TypeVar

from .link_service import create_link, validate_link
from .models import AppSettings, Link


T = TypeVar("T")
DATA_VERSION = 1


@dataclass(frozen=True, slots=True)
class LoadResult(Generic[T]):
    value: T
    existed: bool
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class StoragePaths:
    root: Path
    links_file: Path
    settings_file: Path
    backups_dir: Path

    @classmethod
    def for_user(cls, local_app_data: Path | None = None) -> "StoragePaths":
        base = local_app_data
        if base is None:
            base = (Path.home() / 'Library' / 'Application Support'
                    if sys.platform == 'darwin' else Path(
                        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")))
        root = base / "FloatingLinkDock"
        return cls(
            root=root,
            links_file=root / "links.json",
            settings_file=root / "settings.json",
            backups_dir=root / "backups",
        )


class JsonStore:
    def __init__(self, paths: StoragePaths | None = None) -> None:
        self.paths = paths or StoragePaths.for_user()

    def load_links(self) -> LoadResult[list[Link]]:
        if not self.paths.links_file.exists():
            return LoadResult([], existed=False)
        try:
            payload = self._read_versioned(self.paths.links_file)
            raw_links = payload.get("links")
            if not isinstance(raw_links, list):
                raise ValueError("links must be a list")
            links = [self._parse_link(item) for item in raw_links]
            links.sort(key=lambda item: item.order)
            normalized = [
                replace(item, order=index)
                for index, item in enumerate(links)
            ]
            return LoadResult(normalized, existed=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            backup = self._backup_damaged(self.paths.links_file)
            warning = f"网址数据无法读取，已备份到 {backup.name}：{exc}"
            return LoadResult([], existed=True, warning=warning)

    def save_links(self, links: Sequence[Link]) -> None:
        payload = {
            "version": DATA_VERSION,
            "links": [asdict(link) for link in links],
        }
        self._atomic_write(self.paths.links_file, payload)

    def load_settings(self) -> LoadResult[AppSettings]:
        if not self.paths.settings_file.exists():
            return LoadResult(AppSettings(), existed=False)
        try:
            payload = self._read_versioned(self.paths.settings_file)
            raw = payload.get("settings")
            if not isinstance(raw, dict):
                raise ValueError("settings must be an object")
            settings = AppSettings(
                x=self._optional_int(raw.get("x")),
                y=self._optional_int(raw.get("y")),
                always_on_top=self._bool(raw.get("always_on_top"), True),
                launch_at_startup=self._bool(raw.get("launch_at_startup"), False),
                first_run_complete=self._bool(raw.get("first_run_complete"), False),
                onboarding_complete=self._bool(raw.get("onboarding_complete"), False),
                edge_auto_hide=self._bool(raw.get("edge_auto_hide"), False),
            )
            return LoadResult(settings, existed=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            backup = self._backup_damaged(self.paths.settings_file)
            warning = f"设置无法读取，已备份到 {backup.name}：{exc}"
            return LoadResult(AppSettings(), existed=True, warning=warning)

    def save_settings(self, settings: AppSettings) -> None:
        self._atomic_write(
            self.paths.settings_file,
            {"version": DATA_VERSION, "settings": asdict(settings)},
        )

    @staticmethod
    def _read_versioned(path: Path) -> dict[str, object]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("root must be an object")
        if payload.get("version") != DATA_VERSION:
            raise ValueError("unsupported data version")
        return payload

    @staticmethod
    def _parse_link(raw: object) -> Link:
        if not isinstance(raw, dict):
            raise ValueError("link must be an object")
        link_id = raw.get("id")
        name = raw.get("name")
        url = raw.get("url")
        order = raw.get("order")
        if not isinstance(link_id, str) or not link_id:
            raise ValueError("link id is invalid")
        if not isinstance(name, str) or not name:
            raise ValueError("link name is invalid")
        if not isinstance(url, str) or not url:
            raise ValueError("link url is invalid")
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            raise ValueError("link order is invalid")
        x = JsonStore._optional_int(raw.get("x"))
        y = JsonStore._optional_int(raw.get("y"))
        if (x is not None and x < 0) or (y is not None and y < 0):
            raise ValueError("tile position must not be negative")
        return Link(link_id, name, url, order, x, y)

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("coordinate must be an integer")
        return value

    @staticmethod
    def _bool(value: object, default: bool) -> bool:
        if value is None:
            return default
        if not isinstance(value, bool):
            raise ValueError("setting must be a boolean")
        return value

    def _backup_damaged(self, source: Path) -> Path:
        self.paths.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.paths.backups_dir / f"{source.stem}-{stamp}{source.suffix}"
        shutil.copy2(source, backup)
        return backup

    def _atomic_write(self, target: Path, payload: dict[str, object]) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.paths.root,
                prefix=f"{target.stem}-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def seed_links() -> list[Link]:
    examples = [
        ("飞书", "https://www.feishu.cn"),
        ("GitHub", "https://github.com"),
        ("ChatGPT", "https://chatgpt.com"),
    ]
    return [
        create_link(validate_link(name, url), order=index)
        for index, (name, url) in enumerate(examples)
    ]
