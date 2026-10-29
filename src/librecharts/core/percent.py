"""Shares for 100 % charts (stacked column and bar charts, percent Mekko).

A 100 % chart ignores negative values: they count as empty, like text cells, because a share of a
column only makes sense for positive contributions. The rule is shared with the Mekko parser so
that both chart kinds treat the same data the same way.
"""

from __future__ import annotations

from dataclasses import replace

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import format_share
from librecharts.core.model import Format


def positive_only(data: ChartData) -> ChartData:
    """``data`` with negative and zero values replaced by ``None`` (empty)."""
    return replace(
        data,
        series=tuple(
            replace(s, values=tuple(v if v is not None and v > 0 else None for v in s.values))
            for s in data.series
        ),
    )


def column_total(data: ChartData, category: int) -> float:
    """The sum of the positive values of one column (0 if it has none)."""
    return sum(v for s in data.series if (v := s.values[category]) is not None and v > 0)


def share(value: float | None, total: float) -> float | None:
    """``value`` as a percentage of ``total``; ``None`` if there is no share to draw."""
    if value is None or value <= 0 or total <= 0:
        return None
    return value / total * 100


def share_label(value: float | None, total: float, fmt: Format | None = None) -> str:
    """The label of a segment in a 100 % chart, e.g. ``"33.3%"``."""
    percentage = share(value, total)
    return "" if percentage is None else format_share(percentage, fmt)


def shares(data: ChartData) -> ChartData:
    """``data`` with every positive value replaced by its share of the column (0..100)."""
    totals = [column_total(data, c) for c in range(len(data.categories))]
    return replace(
        data,
        series=tuple(
            replace(
                s,
                values=tuple(share(v, totals[c]) for c, v in enumerate(s.values)),
            )
            for s in data.series
        ),
    )
