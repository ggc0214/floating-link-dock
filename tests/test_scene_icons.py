from queue import SimpleQueue
from floating_link_dock.face_icon import build_face_icon
from floating_link_dock.window import build_app
from floating_link_dock.scene_store import SceneStore
from floating_link_dock.scene_window import build_scenes_app
from floating_link_dock import tray
from test_app_smoke import FakeStore, FakeStartupManager


def test_scene_floating_mark_and_color_are_distinct_from_original(tmp_path):
    old = build_app(FakeStore([]), FakeStartupManager())
    try:
        old_mark = old._button_face.cget('light_image')
        old_color = old.winfo_children()[0].cget('fg_color')
        assert old_mark.tobytes() == build_face_icon().tobytes()
    finally: old.destroy()
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    new = build_scenes_app(store, FakeStartupManager())
    try:
        new_mark = new._button_face.cget('light_image')
        assert new_mark.tobytes() != old_mark.tobytes()
        new_color = new.winfo_children()[0].cget('fg_color')
        assert old_color != new_color
        new.show_panel()
        assert new._header_face.cget('light_image').tobytes() == new_mark.tobytes()
        new.toggle_expanded()
        assert new.winfo_children()[0].cget('fg_color') == new_color
    finally: new.destroy()


def test_scene_tray_receives_distinct_blue_mark(tmp_path, monkeypatch):
    old_image = tray.TrayIcon(SimpleQueue()).icon.icon
    received = []
    class Icon:
        def __init__(self, *args): received.append(args)
        def run_detached(self, **kwargs): pass
        def stop(self): pass
    monkeypatch.setattr(tray.pystray, 'Icon', Icon)
    store = SceneStore(tmp_path / 'new', tmp_path / 'old'); store.initialize(False)
    app = build_scenes_app(store, FakeStartupManager())
    try:
        app.start_desktop_services()
        image = received[0][1]
        assert image.size == (64, 64)
        assert image.tobytes() != old_image.tobytes()
        r, g, b, a = image.getpixel((12, 32))
        assert b > g and b > r and a > 0
    finally: app.destroy()
