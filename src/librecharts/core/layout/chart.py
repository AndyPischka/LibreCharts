"""Lay out a whole chart: pick the layout for the chart kind and apply display options."""

from __future__ import annotations

from librecharts.core import sorting
from librecharts.core.datasheet import ChartData, parse
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.mekko import layout_mekko
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation, ChartState
from librecharts.core.primitives import Primitive
from librecharts.core.waterfall import parse_waterfall


def layout_chart(state: ChartState, width: float, height: float) -> tuple[Primitive, ...]:
    """Primitives for ``state`` in a ``width`` x ``height`` box (1/100 mm).

    Sorting applies to the display only: the layout gets the categories in display order and the
    annotations with their indices moved along, so the stored state never changes.

    Raises ``ValueError`` if the box is too small for the chart.
    """
    if state.kind == "waterfall":
        return layout_waterfall(
            parse_waterfall(state), width, height, state.annotations, state.format
        )
    if state.kind == "mekko":
        return layout_mekko(parse_mekko(state), width, height, state.percent, state.format)
    data, annotations = display_data(state)
    if state.kind == "bar":
        return layout_bar(
            data,
            state.grouping,
            width,
            height,
            annotations,
            percent=state.percent,
            fmt=state.format,
        )
    return layout_column(
        data,
        state.grouping,
        width,
        height,
        annotations,
        percent=state.percent,
        fmt=state.format,
    )


def display_data(state: ChartState) -> tuple[ChartData, tuple[Annotation, ...]]:
    """The data in display order and the annotations moved along with it."""
    data = parse(state)
    order = sorting.order(data, state.grouping, state.sort)
    if order == tuple(range(len(order))):
        return data, state.annotations
    return sorting.sorted_data(data, order), sorting.remap(state.annotations, order)
