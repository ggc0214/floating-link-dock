from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


@dataclass(frozen=True, slots=True)
class ExpansionPlacement:
    origin: Point
    direction: Literal["up", "down"]


def _clamp_axis(value: int, low: int, high: int) -> int:
    if high < low:
        return low
    return min(max(value, low), high)


def clamp_window(
    origin: Point,
    size: tuple[int, int],
    work_area: Rect,
    margin: int = 8,
) -> Point:
    width, height = size
    min_x = work_area.left + margin
    min_y = work_area.top + margin
    max_x = work_area.right - margin - width
    max_y = work_area.bottom - margin - height
    return Point(
        _clamp_axis(origin.x, min_x, max_x),
        _clamp_axis(origin.y, min_y, max_y),
    )


def choose_expansion(
    anchor: Rect,
    panel_size: tuple[int, int],
    work_area: Rect,
    gap: int = 8,
) -> ExpansionPlacement:
    width, height = panel_size
    room_below = work_area.bottom - anchor.bottom - gap
    room_above = anchor.top - work_area.top - gap
    direction: Literal["up", "down"] = (
        "down" if room_below >= height or room_below >= room_above else "up"
    )
    x = anchor.left if direction == "down" else anchor.right - width
    y = anchor.bottom + gap if direction == "down" else anchor.top - gap - height
    origin = clamp_window(Point(x, y), panel_size, work_area)
    return ExpansionPlacement(origin=origin, direction=direction)


def is_drag(start: Point, end: Point, threshold: int = 5) -> bool:
    delta_x = end.x - start.x
    delta_y = end.y - start.y
    return delta_x * delta_x + delta_y * delta_y >= threshold * threshold
