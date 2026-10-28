"""Chart state: the persisted, UNO-free description of one chart."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, get_args

SCHEMA_VERSION = 2

ChartKind = Literal["column", "bar", "waterfall", "mekko"]
Grouping = Literal["stacked", "clustered"]
AnnotationKind = Literal["difference", "cagr", "axis_break"]
ArrowStyle = Literal["bracket", "level"]
LabelMode = Literal["percent", "absolute"]


@dataclass(frozen=True, slots=True)
class Annotation:
    """An arrow or axis break the user placed on a chart.

    ``start`` and ``end`` are category indices; an axis break has ``end == start``. ``series`` is
    ``None`` for a column total and a series index for one bar of a clustered chart. ``style`` and
    ``label`` only matter for difference arrows. Indices are not checked against the data: after a
    data sheet edit an annotation may point past the last category, it is then not drawn.
    """

    kind: AnnotationKind
    start: int
    end: int
    series: int | None = None
    style: ArrowStyle = "bracket"
    label: LabelMode = "percent"

    def __post_init__(self) -> None:
        if self.kind not in get_args(AnnotationKind):
            raise ValueError(f"unknown annotation kind: {self.kind!r}")
        if self.style not in get_args(ArrowStyle):
            raise ValueError(f"unknown arrow style: {self.style!r}")
        if self.label not in get_args(LabelMode):
            raise ValueError(f"unknown label mode: {self.label!r}")
        if min(self.start, self.end, 0 if self.series is None else self.series) < 0:
            raise ValueError("annotation indices must not be negative")
        if self.kind == "axis_break" and self.end != self.start:
            raise ValueError("an axis break belongs to one category")
        if self.kind != "axis_break" and self.end == self.start:
            raise ValueError("an arrow needs two different categories")


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
    annotations: tuple[Annotation, ...] = ()
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
