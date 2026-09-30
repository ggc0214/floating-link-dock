from __future__ import annotations

from floating_link_dock.geometry import (
    Point,
    Rect,
    choose_expansion,
    clamp_window,
    is_drag,
)


WORK = Rect(0, 0, 1920, 1040)


def test_visible_position_is_unchanged() -> None:
    assert clamp_window(Point(100, 120), (52, 52), WORK) == Point(100, 120)


def test_negative_saved_position_is_clamped() -> None:
    assert clamp_window(Point(-900, -40), (52, 52), WORK) == Point(8, 8)


def test_position_beyond_removed_monitor_is_clamped() -> None:
    assert clamp_window(Point(3000, 2000), (52, 52), WORK) == Point(1860, 980)


def test_expands_down_when_space_is_available() -> None:
    placement = choose_expansion(Rect(100, 100, 152, 152), (340, 460), WORK)

    assert placement.direction == "down"
    assert placement.origin == Point(100, 160)


def test_expands_up_near_bottom_edge() -> None:
    placement = choose_expansion(Rect(1200, 970, 1252, 1022), (340, 460), WORK)

    assert placement.direction == "up"
    assert placement.origin == Point(912, 502)


def test_panel_stays_inside_narrow_work_area() -> None:
    work = Rect(0, 0, 300, 500)
    placement = choose_expansion(Rect(260, 230, 292, 262), (340, 460), work)

    assert placement.origin == Point(8, 32)
    assert placement.direction == "down"


def test_five_pixel_motion_distinguishes_click_from_drag() -> None:
    assert is_drag(Point(10, 10), Point(14, 10)) is False
    assert is_drag(Point(10, 10), Point(15, 10)) is True
    assert is_drag(Point(10, 10), Point(13, 14)) is True
