"""The axis break of a column chart: which value range it removes, and the dialog's input rules.

A break removes the values between ``lower`` and ``upper`` from the scale of the whole axis:
everything up to ``lower`` is drawn as is, what lies above ``upper`` continues right after
``lower``. Automatic breaks (no range stored) cut where one column dwarfs the others.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import format_value
from librecharts.core.model import Annotation, Grouping

KEEP = 1.1  # automatic: the break starts this far above the second tallest column
SHOW = 1.3  # automatic: the tallest column continues up to this share of the second tallest


@dataclass(frozen=True, slots=True)
class Break:
    """A value range ``[lower, upper]`` removed from the scale."""

    lower: float
    upper: float

    def fold(self, value: float) -> float:
        """Where ``value`` is drawn on the shortened scale."""
        if value <= self.lower:
            return value
        if value < self.upper:
            return self.lower  # inside the removed range: the column ends at the break
        return value - (self.upper - self.lower)

    def cuts(self, top: float) -> bool:
        """Whether a column reaching ``top`` crosses the break and gets a break mark."""
        return top > self.lower


def column_tops(data: ChartData, grouping: Grouping) -> list[float]:
    """The highest value of every column (0 if it only goes down)."""
    tops: list[float] = []
    for c in range(len(data.categories)):
        values = [v for s in data.series if (v := s.values[c]) is not None]
        if grouping == "clustered":
            tops.append(max([0.0, *values]))
        else:
            tops.append(sum(v for v in values if v > 0))
    return tops


def automatic(tops: list[float]) -> Break | None:
    """The break for columns reaching ``tops``; ``None`` if none dwarfs the others."""
    ranked = sorted(tops, reverse=True)
    if len(ranked) < 2 or ranked[1] <= 0 or ranked[0] <= SHOW * ranked[1]:
        return None
    lower = KEEP * ranked[1]
    return Break(lower, lower + ranked[0] - SHOW * ranked[1])


def resolve(
    annotations: tuple[Annotation, ...], data: ChartData, grouping: Grouping
) -> Break | None:
    """The break to draw: the (last) axis break annotation, if it removes anything here."""
    chosen = next((a for a in reversed(annotations) if a.kind == "axis_break"), None)
    if chosen is None or not data.categories:
        return None
    tops = column_tops(data, grouping)
    if chosen.lower is None or chosen.upper is None:
        return automatic(tops)
    return Break(chosen.lower, chosen.upper) if max(tops) > chosen.upper else None


def describe(annotation: Annotation) -> str:
    """The range of a break for menu titles: ``10-50``, or ``auto``."""
    if annotation.lower is None or annotation.upper is None:
        return "auto"
    return f"{format_value(annotation.lower)}-{format_value(annotation.upper)}"


def check(lower_text: str, upper_text: str, tallest: float) -> tuple[float, float] | str:
    """Validate the dialog's two fields; the range, or the key of the message to show.

    Numbers may use a comma or a dot. The range must lie in ``[0, tallest]``: below zero nothing is
    cut, and a break above the tallest column would remove nothing.
    """
    try:
        lower, upper = _number(lower_text), _number(upper_text)
    except ValueError:
        return "break_not_a_number"
    if lower < 0 or lower >= upper:
        return "break_order"
    if upper > tallest:
        return "break_too_high"
    return lower, upper


def _number(text: str) -> float:
    value = float(text.strip().replace(",", "."))
    if not math.isfinite(value):
        raise ValueError(text)
    return value
