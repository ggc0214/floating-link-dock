# Floating Link Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight Windows floating link dock that expands from a draggable always-on-top button, manages a persistent ordered link list, and ships as editable Python source plus a standalone EXE.

**Architecture:** A small CustomTkinter application will keep UI state separate from pure domain, persistence, geometry, and Windows-integration modules. Pure behavior is covered by pytest; Windows-only behavior is isolated behind narrow functions and verified with mocks plus a final manual acceptance pass. PyInstaller produces the standalone executable after the same source entry point passes all tests.

**Tech Stack:** Python 3.11+, CustomTkinter 5.2.x, Pillow 10+, pytest 8+, PyInstaller 6+, Windows APIs through Python standard library and `ctypes`.

**Spec:** `docs/superpowers/specs/2026-09-30-floating-link-dock-design.md`

## Global Constraints

- Target Windows 10 and Windows 11.
- Deliver editable Python source and a standalone Windows EXE that does not require Python.
- Use one dark graphite theme with mint-cyan as the only accent color.
- Store user data beneath `%LOCALAPPDATA%/FloatingLinkDock`, never beside the installed EXE.
- Do not store passwords, cookies, browser credentials, or other secrets.
- Support a single ordered list only; no groups, tags, search, accounts, cloud sync, or embedded browser.
- Keep the app responsive if storage, browser launch, startup registration, or data parsing fails.
- Respect reduced-motion settings, high DPI, multiple displays, and the active display work area.
- Seed three removable example links only on the first run when no data exists.
- Create and push a private GitHub repository named `floating-link-dock` only after tests, build, and manual smoke checks pass.

## Review Focus

- Reject non-web schemes such as `javascript:`, `file:`, and `data:` instead of passing them to the browser; Task 1 pins this with URL-validation tests.
- Recover from truncated, wrong-version, or structurally invalid JSON without losing the damaged file; Task 2 pins this with recovery tests.
- Preserve the last valid in-memory state when an atomic file replacement fails; Task 2 pins this with a simulated replace failure.
- Return the dock to a visible work area after display removal, scaling changes, or invalid saved coordinates; Task 3 pins this with geometry tests.
- Prevent a second process from creating another dock and activate the existing instance when possible; Task 4 pins this with instance-lock tests.

---

## Planned File Map

```text
src/floating_link_dock/
  __init__.py             Package metadata
  main.py                 Process entry point and dependency wiring
  models.py               Link and settings dataclasses
  link_service.py         Link validation, normalization, naming, and ordering
  storage.py              Atomic JSON persistence and damaged-file recovery
  geometry.py             Pure placement and expansion calculations
  windows_integration.py  DPI, startup, browser, reduced motion, and single instance
  app_controller.py       Save-before-render link mutations and first-run state
  theme.py                Visual tokens and sizing constants
  widgets.py              Link row and inline editor widgets
  window.py               Floating window, collapsed and expanded states
tests/
  test_link_service.py
  test_storage.py
  test_geometry.py
  test_windows_integration.py
  test_app_smoke.py
assets/app.ico
requirements.txt
requirements-dev.txt
pyproject.toml
FloatingLinkDock.spec
run.bat
build.bat
README.md
```

## Task 1: Project Foundation and Link Domain

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `src/floating_link_dock/__init__.py`
- Create: `src/floating_link_dock/models.py`
- Create: `src/floating_link_dock/link_service.py`
- Create: `tests/test_link_service.py`

**Interfaces:**
- Consumes: No earlier task interfaces.
- Produces: `Link(id: str, name: str, url: str, order: int)`, `LinkDraft(name: str, url: str)`, `AppSettings(x: int | None, y: int | None, always_on_top: bool, launch_at_startup: bool, first_run_complete: bool)`, `normalize_url(raw: str) -> str`, `derive_name(url: str) -> str`, `validate_link(name: str, raw_url: str) -> LinkDraft`, `create_link(draft: LinkDraft, order: int) -> Link`, and `reorder_links(links: list[Link], source_index: int, target_index: int) -> list[Link]`.

- [ ] **Step 1: Initialize the local repository and project metadata**

Run `git init`, add a Python-focused `.gitignore`, configure `src` package discovery in `pyproject.toml`, and pin runtime and development dependencies in the two requirements files.

- [ ] **Step 2: Write failing link-domain tests**

Add tests named `test_adds_https_to_bare_domain`, `test_preserves_http_and_https`, `test_rejects_unsafe_schemes`, `test_rejects_missing_host`, `test_derives_name_from_hostname`, `test_create_link_assigns_uuid_and_requested_order`, `test_reorder_returns_new_contiguous_order`, and `test_reorder_rejects_out_of_range_indices`. Assert that only HTTP/HTTPS URLs survive and that reorder results have `order == range(len(result))`.

- [ ] **Step 3: Run the domain tests and verify failure**

Run: `python -m pytest tests/test_link_service.py -q`

Expected: FAIL because `floating_link_dock.models` and `floating_link_dock.link_service` do not exist.

- [ ] **Step 4: Implement domain models and link functions**

Create frozen `Link` and `LinkDraft` dataclasses, mutable `AppSettings`, and the exact public functions listed in Interfaces. Use `urllib.parse.urlparse`; accept only `http` and `https`; require a hostname; strip surrounding whitespace; generate link IDs with UUID4 inside `create_link` only.

- [ ] **Step 5: Run the domain tests**

Run: `python -m pytest tests/test_link_service.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit the domain foundation**

Run: `git add .gitignore pyproject.toml requirements*.txt src/floating_link_dock tests/test_link_service.py && git commit -m "feat: add link domain foundation"`

## Task 2: Safe Local Persistence

**Files:**
- Create: `src/floating_link_dock/storage.py`
- Create: `tests/test_storage.py`

**Interfaces:**
- Consumes: `Link` and `AppSettings` from Task 1.
- Produces: `StoragePaths.for_user(local_app_data: Path | None = None) -> StoragePaths`, `JsonStore.load_links() -> LoadResult[list[Link]]`, `JsonStore.save_links(links: Sequence[Link]) -> None`, `JsonStore.load_settings() -> LoadResult[AppSettings]`, `JsonStore.save_settings(settings: AppSettings) -> None`, and `seed_links() -> list[Link]`.

- [ ] **Step 1: Write failing happy-path persistence tests**

Add `test_paths_live_under_local_app_data`, `test_links_round_trip`, `test_settings_round_trip`, and `test_seed_links_are_created_only_for_missing_first_run_data`. Use pytest `tmp_path` and assert JSON version `1`.

- [ ] **Step 2: Write failing recovery and atomicity tests**

Add `test_truncated_json_is_backed_up_and_returns_empty`, `test_wrong_version_is_backed_up`, `test_invalid_link_shape_is_backed_up`, `test_atomic_replace_failure_keeps_previous_file`, and `test_failed_save_does_not_mutate_callers_list`. Monkeypatch `os.replace` for the failure case and assert the previously valid file still loads.

- [ ] **Step 3: Run storage tests and verify failure**

Run: `python -m pytest tests/test_storage.py -q`

Expected: FAIL because `floating_link_dock.storage` does not exist.

- [ ] **Step 4: Implement versioned reads, atomic writes, and recovery**

Implement the Task 2 interfaces. Write UTF-8 JSON to a same-directory temporary file, flush and `os.fsync`, then call `os.replace`. On read corruption, copy the original into `backups/<stem>-YYYYMMDD-HHMMSS.json`, return a `LoadResult` containing a user-facing warning, and never silently delete the damaged file.

- [ ] **Step 5: Run storage tests**

Run: `python -m pytest tests/test_storage.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit persistence**

Run: `git add src/floating_link_dock/storage.py tests/test_storage.py && git commit -m "feat: add resilient local storage"`

## Task 3: Display-Aware Window Geometry

**Files:**
- Create: `src/floating_link_dock/geometry.py`
- Create: `tests/test_geometry.py`

**Interfaces:**
- Consumes: No platform APIs directly; callers supply `Rect` values.
- Produces: `Rect(left: int, top: int, right: int, bottom: int)`, `Point(x: int, y: int)`, `clamp_window(origin: Point, size: tuple[int, int], work_area: Rect, margin: int = 8) -> Point`, `choose_expansion(anchor: Rect, panel_size: tuple[int, int], work_area: Rect, gap: int = 8) -> ExpansionPlacement`, and `is_drag(start: Point, end: Point, threshold: int = 5) -> bool`.

- [ ] **Step 1: Write failing geometry tests**

Add `test_visible_position_is_unchanged`, `test_negative_saved_position_is_clamped`, `test_position_beyond_removed_monitor_is_clamped`, `test_expands_down_when_space_is_available`, `test_expands_up_near_bottom_edge`, `test_panel_stays_inside_narrow_work_area`, and `test_five_pixel_motion_distinguishes_click_from_drag`.

- [ ] **Step 2: Run geometry tests and verify failure**

Run: `python -m pytest tests/test_geometry.py -q`

Expected: FAIL because `floating_link_dock.geometry` does not exist.

- [ ] **Step 3: Implement pure geometry calculations**

Implement the exact Task 3 interfaces with integer arithmetic. `ExpansionPlacement` must contain `origin: Point` and `direction: Literal["up", "down"]`; clamp every returned placement to the supplied work area margin.

- [ ] **Step 4: Run geometry tests**

Run: `python -m pytest tests/test_geometry.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit geometry**

Run: `git add src/floating_link_dock/geometry.py tests/test_geometry.py && git commit -m "feat: add display-aware window placement"`

## Task 4: Windows Integration Boundaries

**Files:**
- Create: `src/floating_link_dock/windows_integration.py`
- Create: `tests/test_windows_integration.py`

**Interfaces:**
- Consumes: `AppSettings` paths and the packaged/source execution path.
- Produces: `enable_dpi_awareness() -> None`, `get_cursor_work_area() -> Rect`, `system_reduces_motion() -> bool`, `open_in_default_browser(url: str) -> None`, `StartupManager.is_enabled() -> bool`, `StartupManager.set_enabled(enabled: bool) -> None`, and `SingleInstance.acquire(on_second_instance: Callable[[], None]) -> bool` with context-manager cleanup.

- [ ] **Step 1: Write failing integration-boundary tests**

Add `test_browser_uses_validated_url`, `test_startup_command_quotes_paths_with_spaces`, `test_disabling_startup_removes_only_owned_value`, `test_reduced_motion_defaults_safely_when_query_fails`, `test_first_instance_acquires_lock`, and `test_second_instance_fails_lock_and_signals_existing_instance`. Mock registry, browser, mutex, and window-message calls.

- [ ] **Step 2: Run integration tests and verify failure**

Run: `python -m pytest tests/test_windows_integration.py -q`

Expected: FAIL because `floating_link_dock.windows_integration` does not exist.

- [ ] **Step 3: Implement guarded Windows adapters**

Use `ctypes` for DPI awareness, work-area lookup, animation preference, named mutex, and the activation signal. Use the current-user `Run` registry key with the single owned value name `FloatingLinkDock`; use `webbrowser.open_new_tab` for validated URLs. Raise typed `IntegrationError` exceptions with safe user-facing messages.

- [ ] **Step 4: Run integration tests**

Run: `python -m pytest tests/test_windows_integration.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit Windows integration**

Run: `git add src/floating_link_dock/windows_integration.py tests/test_windows_integration.py && git commit -m "feat: add Windows system integration"`

## Task 5: Floating Window and Link Management UI

**Files:**
- Create: `src/floating_link_dock/theme.py`
- Create: `src/floating_link_dock/app_controller.py`
- Create: `src/floating_link_dock/widgets.py`
- Create: `src/floating_link_dock/window.py`
- Create: `src/floating_link_dock/main.py`
- Create: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: All Tasks 1 through 4 interfaces.
- Produces: `AppController.initialize() -> AppSnapshot`, `AppController.add_link(draft: LinkDraft) -> AppSnapshot`, `AppController.edit_link(link_id: str, draft: LinkDraft) -> AppSnapshot`, `AppController.delete_link(link_id: str) -> AppSnapshot`, `AppController.move_link(link_id: str, direction: Literal[-1, 1]) -> AppSnapshot`, `LinkRow`, `InlineLinkEditor`, `FloatingDockWindow`, `build_app(store: JsonStore, startup: StartupManager) -> FloatingDockWindow`, and `main() -> int`.

- [ ] **Step 1: Write failing application wiring tests**

Add `test_first_run_seeds_three_links`, `test_existing_empty_list_stays_empty`, `test_add_edit_delete_and_reorder_persist_before_render`, `test_failed_save_keeps_previous_snapshot`, and `test_corrupt_data_warning_is_exposed_in_snapshot`. Exercise `AppController` with a fake store so tests do not create a real desktop window.

- [ ] **Step 2: Run smoke tests and verify failure**

Run: `python -m pytest tests/test_app_smoke.py -q`

Expected: FAIL because the UI and application wiring modules do not exist.

- [ ] **Step 3: Implement the theme and reusable widgets**

Define graphite surfaces, mint-cyan accent, one radius scale, focus colors, 52-pixel collapsed size, and compact list spacing in `theme.py`. Implement `AppController` so mutations create a candidate list, save it, and only then publish an immutable `AppSnapshot`. Implement `LinkRow` and `InlineLinkEditor`; use Unicode or packaged image assets for icons, never hand-built SVG paths.

- [ ] **Step 4: Implement collapsed and expanded window states**

Implement a borderless `CTk` window with the Task 3 click/drag threshold, saved positioning, up/down expansion, always-on-top toggling, right-click menu, scrollable list, empty state, inline editing, confirmation before deletion, and reduced-motion fallback. Ensure destructive mutations save successfully before replacing rendered state.

- [ ] **Step 5: Wire startup, load warnings, and single-instance activation**

Implement `build_app` and `main`; initialize DPI before constructing the window, acquire the instance guard, seed only on true first run, surface recovery warnings, and return nonzero only when startup cannot continue safely.

- [ ] **Step 6: Run the complete automated suite**

Run: `python -m pytest tests -q`

Expected: all tests PASS.

- [ ] **Step 7: Perform the UI pre-flight review**

Verify one dark theme, one accent, consistent radii, readable button/input contrast, visible keyboard focus, no clipped controls at 100% and 200% scale, no unnecessary decorative labels, motivated state animation only, reduced-motion fallback, and useful empty/error states.

- [ ] **Step 8: Commit the working application**

Run: `git add src/floating_link_dock tests/test_app_smoke.py && git commit -m "feat: build floating link dock interface"`

## Task 6: Packaging, Documentation, Verification, and GitHub Delivery

**Files:**
- Create: `assets/app.ico`
- Create: `FloatingLinkDock.spec`
- Create: `run.bat`
- Create: `build.bat`
- Create: `README.md`
- Create after build: `dist/FloatingLinkDock.exe`

**Interfaces:**
- Consumes: `floating_link_dock.main:main` from Task 5.
- Produces: documented source workflow, reproducible PyInstaller build, verified `dist/FloatingLinkDock.exe`, and private GitHub repository `floating-link-dock`.

- [ ] **Step 1: Add a branded application icon and executable metadata**

Create a simple mint-on-graphite link-dock icon with Windows ICO sizes 16, 24, 32, 48, 64, 128, and 256 pixels. Configure the PyInstaller spec for a windowed one-file executable named `FloatingLinkDock` with CustomTkinter assets collected explicitly.

- [ ] **Step 2: Add source and build launchers**

Create `run.bat` to launch `python -m floating_link_dock.main` using the local environment and `build.bat` to clean the project-owned `build` and `dist` outputs, run the complete tests, then invoke PyInstaller. Both scripts must stop on nonzero exits.

- [ ] **Step 3: Write user and developer documentation**

Document source setup, source launch, EXE launch, `%LOCALAPPDATA%/FloatingLinkDock` data location, startup behavior, controls, troubleshooting, tests, rebuild steps, and the fact that uninstalling the EXE does not automatically delete user links.

- [ ] **Step 4: Run tests immediately before packaging**

Run: `python -m pytest tests -q`

Expected: all tests PASS with no warnings caused by project code.

- [ ] **Step 5: Build the standalone executable**

Run: `build.bat`

Expected: exit code `0` and `dist/FloatingLinkDock.exe` exists.

- [ ] **Step 6: Perform Windows manual acceptance**

Launch the EXE twice and verify single-instance behavior; exercise collapse, expand, drag, edge clamping, add, edit, delete, reorder, browser open, always-on-top, startup toggle, restart persistence, and corrupt-data recovery. Repeat visibility checks at 100%, 125%, 150%, and 200% scaling, and confirm the EXE starts on a Windows account without Python on `PATH`.

- [ ] **Step 7: Commit the release artifacts and documentation**

Run: `git add assets FloatingLinkDock.spec run.bat build.bat README.md && git commit -m "build: package Windows desktop release"`

Do not commit generated `build/`; include the verified EXE in a GitHub Release rather than normal Git history.

- [ ] **Step 8: Create the private GitHub repository and push source**

Run: `gh repo create floating-link-dock --private --source . --remote origin --push`

Expected: the authenticated user's private repository is created, `origin` points to it, and the default branch is pushed.

- [ ] **Step 9: Publish the verified EXE as the first GitHub Release**

Tag the verified commit as `v1.0.0`, push the tag, then run `gh release create v1.0.0 dist/FloatingLinkDock.exe --title "Floating Link Dock v1.0.0" --notes "Windows desktop floating link dock initial release."`

Expected: the private repository has a `v1.0.0` release containing `FloatingLinkDock.exe`.

- [ ] **Step 10: Verify remote delivery**

Run `git status --short`, `git remote -v`, `git log -1 --oneline`, and `gh release view v1.0.0`.

Expected: clean working tree, correct private remote, pushed release commit, and downloadable EXE asset.
