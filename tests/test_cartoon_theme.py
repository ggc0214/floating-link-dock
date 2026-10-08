import customtkinter as ctk

from floating_link_dock import theme
from floating_link_dock.models import AppSettings, Link
from floating_link_dock.tile_layout import TILE_SIZE
from floating_link_dock.window import build_app
from test_app_smoke import FakeStore, FakeStartupManager


def test_cartoon_palette_uses_soft_green_mint_sky_and_yellow():
    assert theme.BACKGROUND == '#EFF8F0'
    assert theme.TILE_COLORS == ('#DDF5E7', '#DEEFFD', '#FFF0B8')
    assert theme.TEXT == '#344B49'
    assert TILE_SIZE == 80


def test_cartoon_widgets_keep_compact_layout_and_links():
    links = [Link(str(i), name, 'https://example.com', i, 8 + i * 92, 8)
             for i, name in enumerate(['飞书', 'GitHub', 'ChatGPT'])]
    app = build_app(FakeStore(links, settings=AppSettings(onboarding_complete=True)),
                    FakeStartupManager())
    try:
        app.update_idletasks()
        app.update()
        button = next(w for w in app.winfo_children() if isinstance(w, ctk.CTkButton))
        assert button.cget('text') == ''
        assert isinstance(button.cget('image'), ctk.CTkImage)
        assert button._image_label.winfo_width() >= round(32 * button._get_widget_scaling())
        assert button.cget('border_width') == 2
        app.show_panel()
        app.update_idletasks()
        for _, tile, link in app.board._items.values():
            assert tile.cget('fg_color') in theme.TILE_COLORS
            assert tile.cget('border_width') == 2
            assert tile.cget('width') == 80
            assert link.url == 'https://example.com'
        assert len(app.snapshot.links) == 3
    finally:
        app.destroy()
