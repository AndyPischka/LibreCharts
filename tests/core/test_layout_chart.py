"""Invariants every chart layout keeps."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date

import pytest

from librecharts.core import datasheet
from librecharts.core.layout.chart import layout_chart
from librecharts.core.model import Annotation, ChartState
from librecharts.core.primitives import (
    MARKER_SIZE,
    Bubble,
    Line,
    Marker,
    Polygon,
    Polyline,
    Primitive,
    Rect,
    Text,
)

SAMPLES: list[Callable[[], ChartState]] = [
    getattr(datasheet, name) for name in dir(datasheet) if name.startswith("sample_")
]
BUBBLES = datasheet.state_from_table(
    "scatter",
    "stacked",
    [
        ["Label", "X", "Y", "Size", "Group"],
        ["Low", 0, 0, 1, None],
        ["Top right", 10, 10, 100, None],
        ["Bottom right", 10, 0, 100, None],
        ["Top left", 0, 10, 100, None],
    ],
)

GO_LIVE = (date(2026, 6, 30) - date(1899, 12, 30)).days  # the sample Gantt chart's last day
LAST_DAY = replace(
    datasheet.sample_gantt_state(),
    annotations=(Annotation("value_line", 0, 0, value=float(GO_LIVE)),),
)


def bounds(p: Primitive) -> tuple[float, float, float, float]:
    """Left, top, right and bottom of the shape drawn for ``p``."""
    if isinstance(p, (Rect, Text)):
        return p.x, p.y, p.x + p.width, p.y + p.height
    if isinstance(p, Line):
        return min(p.x1, p.x2), min(p.y1, p.y2), max(p.x1, p.x2), max(p.y1, p.y2)
    if isinstance(p, (Marker, Bubble)):
        r = (MARKER_SIZE if isinstance(p, Marker) else p.diameter) / 2
        return p.x - r, p.y - r, p.x + r, p.y + r
    assert isinstance(p, (Polyline, Polygon))
    xs, ys = [px for px, _ in p.points], [py for _, py in p.points]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("state", [*(sample() for sample in SAMPLES), BUBBLES, LAST_DAY])
@pytest.mark.parametrize("size", [(9000, 5000), (20000, 12000), (40000, 30000)])
def test_nothing_reaches_out_of_the_box(state: ChartState, size: tuple[int, int]) -> None:
    # The group shape spans its children: anything outside the box grows the group, and every
    # redraw at the group's size (a new colour scheme, say) would widen the chart further.
    width, height = size
    for p in layout_chart(state, width, height):
        left, top, right, bottom = bounds(p)
        assert left >= 0, p
        assert top >= 0, p
        assert right <= width, p
        assert bottom <= height, p
