"""Lay out a whole chart: pick the layout for the chart kind."""

from __future__ import annotations

from librecharts.core.datasheet import parse
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.model import ChartState
from librecharts.core.primitives import Primitive
from librecharts.core.waterfall import parse_waterfall


def layout_chart(state: ChartState, width: float, height: float) -> tuple[Primitive, ...]:
    """Primitives for ``state`` in a ``width`` x ``height`` box (1/100 mm).

    Raises ``ValueError`` if the box is too small for the chart.
    """
    if state.kind == "waterfall":
        return layout_waterfall(parse_waterfall(state), width, height)
    data = parse(state)
    if state.kind == "bar":
        return layout_bar(data, state.grouping, width, height)
    return layout_column(data, state.grouping, width, height)
