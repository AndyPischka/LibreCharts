"""Value lines: a target level or the average across the plot (ADR 0014).

A value line is an axis annotation (``core/model.py``). Its ``value`` is the level it marks;
``None`` means the average of the column sums (on a waterfall: of the levels the steps end at,
on a scatter chart: of the y values).
"""

from __future__ import annotations

import math

from librecharts.core.datasheet import ChartData, parse
from librecharts.core.model import Annotation, ChartState
from librecharts.core.scatter import levels as scatter_levels
from librecharts.core.scatter import parse_scatter
from librecharts.core.waterfall import levels, parse_waterfall


def average(data: ChartData) -> float | None:
    """The mean of the column sums; ``None`` without categories."""
    if not data.categories:
        return None
    sums = [_column_sum(data, c) for c in range(len(data.categories))]
    return sum(sums) / len(sums)


def _column_sum(data: ChartData, category: int) -> float:
    total = 0.0
    for series in data.series:
        value = series.values[category]
        if value is not None:
            total += value
    return total


def average_for(state: ChartState) -> float | None:
    """The average a value line of ``state`` shows when it has no explicit value."""
    if state.kind == "waterfall":
        measured = levels(parse_waterfall(state))
        steps = [v for v in measured.series[0].values if v is not None]
        return sum(steps) / len(steps) if steps else None
    if state.kind == "scatter":
        return average(scatter_levels(parse_scatter(state)))
    return average(parse(state))


def resolved(annotation: Annotation, data: ChartData) -> float | None:
    """The level ``annotation`` marks on ``data`` (the average if it has no value)."""
    return annotation.value if annotation.value is not None else average(data)


def check(text: str) -> float | str:
    """Validate the dialog's value field: a finite number, or the error message key."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return "value_line_not_a_number"
    if not math.isfinite(value):
        return "value_line_not_a_number"
    return value
