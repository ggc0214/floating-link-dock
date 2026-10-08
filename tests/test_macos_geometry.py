from types import SimpleNamespace

import pytest
from floating_link_dock import macos_integration as mi
from floating_link_dock.geometry import Point, Rect


def test_cocoa_visible_rect_to_tk():
    assert mi.cocoa_to_tk((0, 40, 1440, 836), 900) == Rect(0, 24, 1440, 860)
    assert mi.cocoa_to_tk((-1280, 0, 1280, 900), 900) == Rect(-1280, 0, 0, 900)
    assert mi.cocoa_to_tk((0, 900, 1440, 900), 900) == Rect(0, -900, 1440, 0)


@pytest.mark.parametrize('point,expected', [
    (Point(500, 100), Rect(0, 24, 1440, 860)),
    (Point(-500, 50), Rect(-1280, 0, 0, 900)),
    (Point(500, -500), Rect(0, -900, 1440, 0)),
    (Point(2000, 400), Rect(0, 24, 1440, 860)),
])
def test_select_screen(monkeypatch, point, expected):
    monkeypatch.setattr(mi, '_screen_rects', lambda: [
        (Rect(0, 0, 1440, 900), Rect(0, 24, 1440, 860)),
        (Rect(-1280, 0, 0, 900), Rect(-1280, 0, 0, 900)),
        (Rect(0, -900, 1440, 0), Rect(0, -900, 1440, 0)),
    ])
    assert mi.get_work_area_for_point(point) == expected


def test_control_click_cancels_tile_open():
    from floating_link_dock.tile_board import TileBoard
    board = SimpleNamespace(_active='one', _drag_start=Point(10, 10))
    board._menu = lambda key, event: None
    assert TileBoard._context_click(board, 'one', SimpleNamespace()) == 'break'
    assert board._active is None
    assert board._drag_start is None
