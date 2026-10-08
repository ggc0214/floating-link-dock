# Mac continuation instructions

This folder is the latest source handoff for the FloatingLinkDock Apple Silicon version. The design and implementation plan are already approved. Do not restart design or use an older GitHub checkout in place of these files.

Read first:
- docs/macos/交付状态.md
- docs/macos/使用说明.md
- docs/macos/实施记录.md
- docs/superpowers/specs/2026-10-08-macos-arm64-design.md
- docs/superpowers/plans/2026-10-08-macos-arm64.md

Continue on this Mac: inspect macOS/Python/Tk and arm64 architecture; use a project-specific virtual environment; install requirements-dev.txt; run the full test suite; fix failures with focused regression tests; run bash scripts/build_macos.sh. Keep build outputs under dist/macos-arm64.

The Windows-host test evidence is historical, not Mac acceptance. Native .app building, menu/Tk coexistence, Retina/multimonitor geometry, Finder reopening, real POSIX process locks, browser opening, login startup, and second-machine sharing still require Mac validation. Report any validation that needs the user's interaction.

Preserve Windows functionality and existing changes. Do not export personal URLs, credentials, auth/config files, or logs. Do not use sudo or disable system-wide security checks. Do not push, create cloud jobs, publish, purchase signing services or use Apple credentials without explicit authorization. Ad-hoc signing is not Developer ID signing or notarization.

This ZIP has no .git history and contains uncommitted current working files. Do not initialize a repository or pretend the previous local branch exists here unless the user requests repository setup. Use the portable relative paths above, not embedded old D:/xuanfu paths in historical notes.

Use a visualization only when it materially helps explain a complex relationship.
