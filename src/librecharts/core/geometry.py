"""Circle geometry for pie and doughnut charts (and later Harvey balls).

Angles are degrees, clockwise from 12 o'clock, like the segments of a pie chart.
"""

from __future__ import annotations

import math

POINTS_PER_DEGREE = 1  # arc resolution; the point count depends on the sweep, never on the size


def polar(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    """The point ``radius`` from the centre at ``angle`` degrees (clockwise from 12 o'clock)."""
    radians = math.radians(angle)
    return cx + radius * math.sin(radians), cy - radius * math.cos(radians)


def sector(
    cx: float, cy: float, outer: float, inner: float, start: float, end: float
) -> tuple[tuple[float, float], ...]:
    """The outline of a pie (``inner == 0``) or doughnut segment from ``start`` to ``end``.

    A pie segment runs from the centre to the arc; a doughnut segment along the outer arc and back
    along the inner one. The outline is open: the renderer closes the polygon. The number of points
    depends only on the sweep, so a resize keeps the primitive structure (ADR 0007).
    """
    if outer <= 0 or not 0 <= inner < outer:
        raise ValueError("a sector needs 0 <= inner < outer")
    if end < start:
        raise ValueError("a sector must not end before it starts")
    steps = max(1, math.ceil((end - start) * POINTS_PER_DEGREE))
    angles = [start + (end - start) * i / steps for i in range(steps + 1)]
    outline = [polar(cx, cy, outer, angle) for angle in angles]
    if inner == 0:
        return ((cx, cy), *outline)
    return (*outline, *(polar(cx, cy, inner, angle) for angle in reversed(angles)))
