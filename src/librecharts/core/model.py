"""Chart state: the persisted, UNO-free description of one chart."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, get_args

SCHEMA_VERSION = 1

ChartKind = Literal["column", "bar", "waterfall", "mekko"]
Grouping = Literal["stacked", "clustered"]


@dataclass(frozen=True, slots=True)
class ChartState:
    """Everything needed to redraw and re-edit a chart.

    ``cells`` holds the raw data sheet contents as Calc returns them (numbers, text and formulas
    such as ``=B2*2``). ``values`` holds the evaluated numbers the chart is drawn from, ``None``
    where a cell is empty or not numeric. Both grids are rectangular and have the same shape.
    """

    kind: ChartKind
    grouping: Grouping
    cells: tuple[tuple[str, ...], ...]
    values: tuple[tuple[float | None, ...], ...]
    version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.kind not in get_args(ChartKind):
            raise ValueError(f"unknown chart kind: {self.kind!r}")
        if self.grouping not in get_args(Grouping):
            raise ValueError(f"unknown grouping: {self.grouping!r}")
        if len(self.cells) != len(self.values):
            raise ValueError("cells and values must have the same number of rows")
        widths = {len(row) for row in (*self.cells, *self.values)}
        if len(widths) > 1:
            raise ValueError("cells and values must be rectangular and of equal width")
        if any(v is not None and not math.isfinite(v) for row in self.values for v in row):
            raise ValueError("values must be finite numbers or None")
