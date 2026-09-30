from __future__ import annotations

from pathlib import Path

import pytest

import floating_link_dock.windows_integration as wi


class MemoryRegistry:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def OpenKey(self, *_args, **_kwargs):
        return self

    def QueryValueEx(self, _key, name: str):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], self.REG_SZ

    def SetValueEx(self, _key, name: str, _reserved, _kind, value: str) -> None:
        self.values[name] = value

    def DeleteValue(self, _key, name: str) -> None:
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


def test_browser_uses_validated_url(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(wi.webbrowser, "open_new_tab", lambda url: opened.append(url) or True)

    wi.open_in_default_browser("example.com")

    assert opened == ["https://example.com"]
    with pytest.raises(wi.IntegrationError):
        wi.open_in_default_browser("javascript:alert(1)")


def test_startup_command_quotes_paths_with_spaces() -> None:
    manager = wi.StartupManager(
        executable=Path(r"C:\Program Files\Floating Link Dock\FloatingLinkDock.exe"),
        registry=MemoryRegistry(),
    )

    assert manager.command == '"C:\\Program Files\\Floating Link Dock\\FloatingLinkDock.exe"'


def test_disabling_startup_removes_only_owned_value() -> None:
    registry = MemoryRegistry()
    registry.values = {"FloatingLinkDock": '"C:\\Dock.exe"', "OtherApp": "other.exe"}
    manager = wi.StartupManager(Path(r"C:\Dock.exe"), registry=registry)

    manager.set_enabled(False)

    assert registry.values == {"OtherApp": "other.exe"}


def test_startup_enabled_requires_matching_command() -> None:
    registry = MemoryRegistry()
    manager = wi.StartupManager(Path(r"C:\Dock.exe"), registry=registry)

    manager.set_enabled(True)
    assert manager.is_enabled() is True
    registry.values["FloatingLinkDock"] = '"C:\\Different.exe"'
    assert manager.is_enabled() is False


def test_reduced_motion_defaults_safely_when_query_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wi, "_query_client_area_animation", lambda: (_ for _ in ()).throw(OSError("no")))

    assert wi.system_reduces_motion() is False


class FakeMutexApi:
    ERROR_ALREADY_EXISTS = 183

    def __init__(self) -> None:
        self.exists = False
        self.last_error = 0
        self.closed: list[int] = []

    def create_mutex(self, _name: str) -> int:
        self.last_error = self.ERROR_ALREADY_EXISTS if self.exists else 0
        self.exists = True
        return 42

    def get_last_error(self) -> int:
        return self.last_error

    def close_handle(self, handle: int) -> None:
        self.closed.append(handle)


def test_first_instance_acquires_lock() -> None:
    guard = wi.SingleInstance("test", api=FakeMutexApi())

    assert guard.acquire(lambda: None) is True
    guard.close()

    assert guard._api.closed == [42]


def test_second_instance_fails_lock_and_signals_existing_instance() -> None:
    api = FakeMutexApi()
    first = wi.SingleInstance("test", api=api)
    second = wi.SingleInstance("test", api=api)
    signals: list[str] = []
    assert first.acquire(lambda: None) is True

    assert second.acquire(lambda: signals.append("activate")) is False

    assert signals == ["activate"]
    assert api.closed == [42]
    first.close()
