"""Lay out a whole chart: pick the layout for the chart kind and apply display options."""

from __future__ import annotations

from librecharts.core import sorting
from librecharts.core.datasheet import ChartData, parse
from librecharts.core.layout.area import layout_area
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.line import layout_line
from librecharts.core.layout.mekko import layout_mekko
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation, ChartState
from librecharts.core.primitives import Primitive
from librecharts.core.waterfall import parse_waterfall


def layout_chart(
    state: ChartState, width: float, height: float, length_per_unit: float | None = None
) -> tuple[Primitive, ...]:
    """Primitives for ``state`` in a ``width`` x ``height`` box (1/100 mm).

    Sorting applies to the display only: the layout gets the categories in display order and the
    annotations with their indices moved along, so the stored state never changes. A chart in a
    same-scale group passes the group's ``length_per_unit`` (ADR 0017).

    Raises ``ValueError`` if the box is too small for the chart.
    """
    if state.kind == "waterfall":
        return layout_waterfall(
            parse_waterfall(state),
            width,
            height,
            state.annotations,
            state.format,
            length_per_unit,
        )
    if state.kind == "mekko":
        return layout_mekko(
            parse_mekko(state), width, height, state.percent, state.format, length_per_unit
        )
    data, annotations = display_data(state)
    if state.kind == "line":
        return layout_line(data, width, height, annotations, state.format, length_per_unit)
    if state.kind == "area":
        return layout_area(
            data,
            state.grouping,
            width,
            height,
            annotations,
            percent=state.percent,
            fmt=state.format,
            length_per_unit=length_per_unit,
        )
    if state.kind == "bar":
        return layout_bar(
            data,
            state.grouping,
            width,
            height,
            annotations,
            percent=state.percent,
            fmt=state.format,
            length_per_unit=length_per_unit,
        )
    return layout_column(
        data,
        state.grouping,
        width,
        height,
        annotations,
        percent=state.percent,
        fmt=state.format,
        lines=state.lines,
        secondary=state.secondary,
        length_per_unit=length_per_unit,
    )


def display_data(state: ChartState) -> tuple[ChartData, tuple[Annotation, ...]]:
    """The data in display order and the annotations moved along with it."""
    data = parse(state)
    order = sorting.order(data, state.grouping, state.sort)
    if order == tuple(range(len(order))):
        return data, state.annotations
    return sorting.sorted_data(data, order), sorting.remap(state.annotations, order)
