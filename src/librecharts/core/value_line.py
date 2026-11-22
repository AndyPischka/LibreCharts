"""Value lines: a target level, the average or the median across the plot (ADR 0014).

A value line is an axis annotation (``core/model.py``). Its ``value`` is the level it marks;
``None`` means a statistic of the measured data: the average of the column sums by default, the
median with ``value_line_mode="median"`` (M32) — on a waterfall of the levels the steps end at,
on a scatter chart of the y values. On a Gantt chart a value line is a date line: its value is a
Calc serial number, entered as a date.
"""

from __future__ import annotations

import math
import re
from datetime import date

from librecharts.core.datasheet import ChartData, parse
from librecharts.core.gantt import serial, to_date
from librecharts.core.locale_format import numeric_date
from librecharts.core.model import Annotation, ChartState, ValueLineMode
from librecharts.core.scatter import levels as scatter_levels
from librecharts.core.scatter import parse_scatter
from librecharts.core.waterfall import levels, parse_waterfall


def average(data: ChartData) -> float | None:
    """The mean of the column sums; ``None`` without categories."""
    if not data.categories:
        return None
    sums = [_column_sum(data, c) for c in range(len(data.categories))]
    return sum(sums) / len(sums)


def median(data: ChartData) -> float | None:
    """The median of the column sums; ``None`` without categories.

    An even number of sums takes the mean of the two middle ones.
    """
    if not data.categories:
        return None
    sums = sorted(_column_sum(data, c) for c in range(len(data.categories)))
    middle = len(sums) // 2
    if len(sums) % 2:
        return sums[middle]
    return (sums[middle - 1] + sums[middle]) / 2


def _column_sum(data: ChartData, category: int) -> float:
    total = 0.0
    for series in data.series:
        value = series.values[category]
        if value is not None:
            total += value
    return total


def statistic(data: ChartData, mode: ValueLineMode | None) -> float | None:
    """The level a value line with ``mode`` marks on ``data``: the average, or the median."""
    if mode == "median":
        return median(data)
    return average(data)


def statistic_for(state: ChartState, mode: ValueLineMode | None) -> float | None:
    """The statistic a value line of ``state`` shows when it has no explicit value."""
    if state.kind == "waterfall":
        return statistic(levels(parse_waterfall(state)), mode)
    if state.kind == "scatter":
        return statistic(scatter_levels(parse_scatter(state)), mode)
    return statistic(parse(state), mode)


def average_for(state: ChartState) -> float | None:
    """The average a value line of ``state`` shows when it has no explicit value."""
    return statistic_for(state, "average")


def resolved(annotation: Annotation, data: ChartData) -> float | None:
    """The level ``annotation`` marks on ``data`` (a statistic of it if it has no value)."""
    if annotation.value is not None:
        return annotation.value
    return statistic(data, annotation.value_line_mode)


def check(text: str) -> float | str:
    """Validate the dialog's value field: a finite number, or the error message key."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return "value_line_not_a_number"
    if not math.isfinite(value):
        return "value_line_not_a_number"
    return value


def check_date(text: str, language: str) -> float | str:
    """Validate the date field of a Gantt chart's date line: its serial number, or the error key.

    Accepted: ISO ``2026-06-30`` always, ``30.6.2026`` (day first) always, and ``6/30/2026`` in
    English or ``30/6/2026`` in other languages. Two-digit years mean 20xx.
    """
    parts = re.fullmatch(r"\s*(\d{1,4})([-./])(\d{1,2})\2(\d{1,4})?\s*", text)
    if parts is None:
        return "date_line_invalid"
    first, separator, second, third = parts.groups()
    if separator == "-":
        if third is None or len(first) != 4:
            return "date_line_invalid"
        year, month, day = first, second, third
    elif separator == "/" and language == "en":
        month, day, year = first, second, third
    else:
        day, month, year = first, second, third
    if year is None:  # "30.06." without a year
        return "date_line_invalid"
    number = int(year) + (2000 if len(year) <= 2 else 0)
    try:
        found = date(number, int(month), int(day))
    except ValueError:
        return "date_line_invalid"
    if to_date(serial(found)) is None:
        return "date_line_invalid"
    return float(serial(found))


def date_input(value: float, language: str) -> str:
    """A date line's value as the dialog shows it: ``30.06.2026`` in German, ``30/06/2026`` in
    French, Spanish and Italian, else ISO."""
    day = to_date(value)
    if day is None:
        return ""
    return numeric_date(day, language)
