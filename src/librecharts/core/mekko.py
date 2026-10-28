"""Data sheet conventions for Marimekko (percent Mekko) charts.

The data sheet looks like a column chart's (category names in the first row, one row per series)
plus an optional width row directly below the names: a row whose name is "Width" or "Breite".

- Every column is drawn 100 % high; a segment's height is its share of the column's sum.
- A column's width is its value in the width row or, if that cell is empty or there is no width
  row, the sum of its segments.
- Negative values make no sense in a percent Mekko and count as empty, like text.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from librecharts.core.datasheet import ChartData, parse
from librecharts.core.model import ChartState

WIDTH_ROW_NAMES = frozenset({"width", "breite"})


@dataclass(frozen=True, slots=True)
class MekkoData:
    data: ChartData  # segment values; negatives already replaced by None
    widths: tuple[float, ...]  # one per category, >= 0


def has_width_row(state: ChartState) -> bool:
    return len(state.cells) > 1 and state.cells[1][0].strip().lower() in WIDTH_ROW_NAMES


def parse_mekko(state: ChartState) -> MekkoData:
    width_row: tuple[float | None, ...] = ()
    if has_width_row(state):
        width_row = state.values[1]
        state = replace(
            state,
            cells=state.cells[:1] + state.cells[2:],
            values=state.values[:1] + state.values[2:],
        )
    data = parse(state)
    data = ChartData(
        data.categories,
        tuple(
            replace(s, values=tuple(v if v is not None and v > 0 else None for v in s.values))
            for s in data.series
        ),
    )
    widths: list[float] = []
    for c in range(len(data.categories)):
        given = width_row[c + 1] if c + 1 < len(width_row) else None
        column_sum = sum(v for s in data.series if (v := s.values[c]) is not None)
        widths.append(given if given is not None and given > 0 else column_sum)
    return MekkoData(data, tuple(widths))
