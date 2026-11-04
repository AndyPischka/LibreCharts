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
# Charts whose labels leave their segments (M16): flat segments fill the label lanes, negative
# columns and bars label at their negative end, and close line values and tiny pie segments
# spread apart. None of that may reach out of the box.
FLAT_COLUMN = datasheet.state_from_table("column", "stacked", [[None, "X"], ["A", 999], ["B", 1]])
FLAT_BAR = datasheet.state_from_table("bar", "stacked", [[None, "X"], ["A", 999], ["B", 1]])
FLAT_PERCENT_COLUMN = replace(
    datasheet.state_from_table("column", "stacked", [[None, "X"], ["A", 90], ["B", 5], ["C", 5]]),
    percent=True,
)
FLAT_PERCENT_BAR = replace(
    datasheet.state_from_table("bar", "stacked", [[None, "X"], ["A", 90], ["B", 5], ["C", 5]]),
    percent=True,
)
NEGATIVE_COLUMN = datasheet.state_from_table(
    "column", "stacked", [[None, "X"], ["A", -999], ["B", -1]]
)
NEGATIVE_BAR = datasheet.state_from_table("bar", "stacked", [[None, "X"], ["A", -999], ["B", -1]])
MIXED_COLUMN = datasheet.state_from_table("column", "stacked", [[None, "X"], ["A", 5], ["B", -3]])
CLOSE_LINES = datasheet.state_from_table(
    "line",
    "stacked",
    [[None, "X"], ["A", 10], ["B", 10], ["C", 10], ["D", 10], ["E", 10], ["F", 10], ["G", 10]],
)
TINY_PIE = datasheet.state_from_table(
    "pie",
    "stacked",
    [[None, "X"], ["A", 1], ["B", 1], ["C", 1], ["D", 1], ["E", 1], ["F", 1], ["G", 92]],
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


@pytest.mark.parametrize(
    "state",
    [
        *(sample() for sample in SAMPLES),
        BUBBLES,
        LAST_DAY,
        FLAT_COLUMN,
        FLAT_BAR,
        FLAT_PERCENT_COLUMN,
        FLAT_PERCENT_BAR,
        NEGATIVE_COLUMN,
        NEGATIVE_BAR,
        MIXED_COLUMN,
        CLOSE_LINES,
        TINY_PIE,
    ],
)
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


def test_a_floating_bar_chart_lays_out_from_and_to_levels() -> None:
    state = replace(
        datasheet.state_from_table(
            "column",
            "clustered",
            [[None, "A", "B"], ["Low", 2, 5], ["High", 10, 20]],
        ),
        range=True,
    )
    primitives = layout_chart(state, 2000, 10000)
    bars = [p for p in primitives if isinstance(p, Rect)]
    assert [(b.y, b.height) for b in bars] == [(4900.0, 3280.0), (800.0, 6150.0)]
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["10", "20"]


def test_a_floating_bar_chart_sorts_its_categories_with_the_bases() -> None:
    state = replace(
        datasheet.state_from_table(
            "column",
            "clustered",
            [[None, "A", "B"], ["Low", 2, 5], ["High", 10, 20]],
        ),
        range=True,
        sort="descending",
    )
    primitives = layout_chart(state, 2000, 10000)
    names = [p.text for p in primitives if isinstance(p, Text) and p.role == "category"]
    assert names == ["B", "A"]  # sorted by the to values


def test_an_error_bar_chart_scales_to_value_plus_error() -> None:
    state = replace(
        datasheet.state_from_table(
            "line",
            "stacked",
            [[None, "A", "B"], ["Sales", 10, 20], ["Error", 2, 5]],
        ),
        errors=True,
    )
    primitives = layout_chart(state, 3000, 10000)
    whiskers = [p for p in primitives if isinstance(p, Line) and p.role == "annotation"]
    assert len(whiskers) == 6  # two points, a whisker line and two caps each
    assert not any(
        isinstance(p, Text) and p.role == "value" and p.text == "25" for p in primitives
    )  # the whisker top is not labelled


def test_a_sorted_pie_keeps_its_categories_and_orders_its_segments() -> None:
    state = replace(datasheet.sample_pie_state(), sort="descending")
    primitives = layout_chart(state, 8000, 4000)
    names = [p.text for p in primitives if isinstance(p, Text) and p.role == "category"]
    assert names == ["2024", "2025"]  # categories stay in data sheet order
    sectors = [p for p in primitives if isinstance(p, Polygon)]
    assert [s.series for s in sectors[:3]] == [0, 1, 2]  # 2024: 40 > 35 > 25
    assert [s.series for s in sectors[3:]] == [1, 0, 2]  # 2025: B=38, A=35, C=27
