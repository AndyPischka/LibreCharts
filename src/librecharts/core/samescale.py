"""Same-scale groups: several charts draw the same value with the same length (ADR 0017).

A group is a document-wide id stored in ``ChartState.scale_group``. Charts in one group share a
length per value unit: the smallest natural scale of the group, so the tightest chart still fits.
Pure Python, no UNO: the adapter passes the current size of every chart.

Only charts with a comparable value axis can join: vertical charts (column, line, area, waterfall
and a units Mekko) with each other, bar charts (horizontal) with each other. Percent charts have a
fixed 0..100 scale of their own and never join.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from librecharts.core.layout import area, bar, column, line, mekko, waterfall
from librecharts.core.layout.chart import display_data
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import ChartState
from librecharts.core.waterfall import parse_waterfall

Orientation = Literal["vertical", "horizontal"]

VERTICAL_KINDS = frozenset({"column", "line", "area", "waterfall"})

ChartSize = tuple[ChartState, float, float]


def orientation(state: ChartState) -> Orientation | None:
    """How the chart grows values, or ``None`` if it has no comparable value scale."""
    if state.percent:
        return None
    if state.kind == "mekko":
        return "vertical"
    if state.kind == "bar":
        return "horizontal"
    if state.kind in VERTICAL_KINDS:
        return "vertical"
    return None


def joinable(state: ChartState) -> bool:
    """Whether the chart has a value scale that a same-scale group can share."""
    return orientation(state) is not None


def can_join(charts: Sequence[ChartState]) -> bool:
    """Whether all ``charts`` could go into one group (at least one, all the same orientation)."""
    if not charts:
        return False
    first = orientation(charts[0])
    return first is not None and all(orientation(state) == first for state in charts)


def natural_length_per_unit(state: ChartState, width: float, height: float) -> float | None:
    """How many 1/100 mm one value unit gets when ``state`` is drawn alone in the box."""
    if orientation(state) is None:
        return None
    if state.kind == "waterfall":
        return waterfall.natural_length_per_unit(
            parse_waterfall(state), width, height, state.annotations, state.format
        )
    if state.kind == "mekko":
        return mekko.natural_length_per_unit(
            parse_mekko(state), width, height, state.percent, state.format
        )
    data, annotations = display_data(state)
    if not data.categories or not data.series:
        return None
    if state.kind == "line":
        return line.natural_length_per_unit(data, width, height, annotations, state.format)
    if state.kind == "area":
        return area.natural_length_per_unit(
            data, width, height, annotations, state.percent, state.format
        )
    if state.kind == "bar":
        return bar.natural_length_per_unit(
            data, state.grouping, width, height, annotations, state.percent, state.format
        )
    return column.natural_length_per_unit(
        data,
        state.grouping,
        width,
        height,
        annotations,
        state.percent,
        state.format,
        state.lines,
        state.secondary,
    )


def common_length_per_unit(charts: Sequence[ChartSize]) -> float | None:
    """The group's length per unit: the smallest natural scale of its charts.

    ``None`` if there is nothing to scale: an empty group, a percent chart, or charts of different
    orientations. ``charts`` holds every chart of the group with its current width and height.
    """
    if not charts or not can_join([state for state, _, _ in charts]):
        return None
    lengths = [
        length
        for state, width, height in charts
        if (length := natural_length_per_unit(state, width, height)) is not None
    ]
    return min(lengths) if lengths else None


__all__ = [
    "ChartSize",
    "Orientation",
    "can_join",
    "common_length_per_unit",
    "joinable",
    "natural_length_per_unit",
    "orientation",
]
