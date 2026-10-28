"""Pieces shared by the column and bar layouts."""

from __future__ import annotations

from librecharts.core.datasheet import ChartData
from librecharts.core.model import Grouping
from librecharts.core.scale import Axis, nice_axis

GAP_RATIO = 0.3  # share of a category slot left empty between columns or bars


def format_value(value: float) -> str:
    """Locale-neutral label text: integers plain, others with at most two decimals."""
    if value == round(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def value_axis(data: ChartData, grouping: Grouping) -> Axis:
    """The value range covering all segments (stacked: per-category sums), always including zero."""
    if grouping == "stacked":
        lows: list[float] = []
        highs: list[float] = []
        for c in range(len(data.categories)):
            column = [v for s in data.series if (v := s.values[c]) is not None]
            lows.append(sum(v for v in column if v < 0))
            highs.append(sum(v for v in column if v > 0))
        return nice_axis(min(lows), max(highs))
    values = [v for s in data.series for v in s.values if v is not None]
    return nice_axis(min(values, default=0.0), max(values, default=0.0))
