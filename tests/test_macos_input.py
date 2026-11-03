"""Regression for keyboard focus in the real accessory-mode Mac editor."""
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='native Mac keyboard focus')
@pytest.mark.parametrize('mode', ['add', 'edit', 'repeat'])
def test_mac_editor_receives_keys_after_opening_and_switching_fields(tmp_path, mode):
    # Removing the editor's mapped-window focus handling must break this test.
    # Cocoa/Tk lifecycle is process-global, so use one app per subprocess.
    subprocess.run([
        sys.executable, '-c',
        'import runpy,sys; from pathlib import Path; '
        'sys.path.insert(0,str(Path(sys.argv[1]).parents[1]/"src")); '
        'runpy.run_path(sys.argv[1])["_check_editor"](Path(sys.argv[2]),sys.argv[3])',
        str(Path(__file__).resolve()), str(tmp_path), mode,
    ], check=True, timeout=30)


def _check_editor(tmp_path, mode):
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
    from floating_link_dock.window import build_app
    from floating_link_dock.widgets import InlineLinkEditor
    from floating_link_dock.storage import JsonStore, StoragePaths
    from floating_link_dock.macos_lifecycle import StartupManager

    app = build_app(JsonStore(StoragePaths.for_user(tmp_path / 'data')),
                    StartupManager(tmp_path / 'Test.app', agents_dir=tmp_path / 'agents'))

    def editor_in(widget):
        if isinstance(widget, InlineLinkEditor):
            return widget
        for child in widget.winfo_children():
            found = editor_in(child)
            if found is not None:
                return found

    try:
        app.start_desktop_services()
        app.show_panel()
        app.update()
        native = next(window for window in NSApplication.sharedApplication().windows()
                      if window.title() == app.title())
        assert native.canBecomeKeyWindow(), 'dock refuses native keyboard focus'
        assert native.styleMask() == 0, 'Mac dock must remain borderless'
        if mode == 'repeat':
            for index in range(5):
                app.withdraw()
                app.update()
                app.show_panel()
                app._begin_add()
                app.update()
                editor = editor_in(app)
                assert app.focus_get() is editor.name_entry._entry
                assert native.isKeyWindow(), 'editor cannot recover native focus'
                editor.name_entry._entry.event_generate('<KeyPress>', keysym='a')
                app.update()
                assert editor.name_entry.get() == 'a'
                editor.url_entry.insert(0, f'https://example.com/{index}')
                editor._submit()
                app.update()
                added = app.snapshot.links[-1]
                app._begin_edit(added)
                app.update()
                editor = editor_in(app)
                assert app.focus_get() is editor.name_entry._entry
                editor.name_entry._entry.event_generate('<KeyPress>', keysym='b')
                app.update()
                assert editor.name_entry.get() == 'ab'
                editor._submit()
                app.update()
                assert app.snapshot.links[-1].name == 'ab'
                assert native.canBecomeKeyWindow()
            saved = JsonStore(StoragePaths.for_user(tmp_path / 'data')).load_links()
            assert [link.name for link in saved.value[-5:]] == ['ab'] * 5
            return
        if mode == 'add':
            app._begin_add()
        else:
            app._begin_edit(app.snapshot.links[0])
        app.update()
        editor = editor_in(app)
        assert app.focus_get() is editor.name_entry._entry, 'editor has no keyboard focus'
        for entry in (editor.url_entry, editor.name_entry):
            entry.delete(0, 'end')
            # Exercise the bound click/focus path, not direct Entry.insert().
            entry._entry.event_generate('<ButtonPress-1>', x=10, y=10)
            app.update()
            assert app.focus_get() is entry._entry
            entry._entry.event_generate('<KeyPress>', keysym='a')
            app.update()
            assert entry.get() == 'a'
        assert NSApplication.sharedApplication().activationPolicy() == NSApplicationActivationPolicyAccessory
        editor._submit()
        assert editor.error_label.cget('text'), 'invalid URL should remain rejected'
    finally:
        app.destroy()
