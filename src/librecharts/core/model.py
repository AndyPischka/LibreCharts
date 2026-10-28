"""Chart state: the persisted, UNO-free description of one chart."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, get_args

SCHEMA_VERSION = 3

ChartKind = Literal["column", "bar", "waterfall", "mekko"]
Grouping = Literal["stacked", "clustered"]
AnnotationKind = Literal["difference", "cagr", "axis_break"]
ArrowStyle = Literal["bracket", "level"]
LabelMode = Literal["percent", "absolute"]


@dataclass(frozen=True, slots=True)
class Annotation:
    """An arrow or axis break the user placed on a chart.

    ``start`` and ``end`` are category indices. ``series`` is ``None`` for a column total and a
    series index for one bar of a clustered chart. ``style`` and ``label`` only matter for
    difference arrows. Indices are not checked against the data: after a data sheet edit an
    annotation may point past the last category, it is then not drawn.

    An axis break belongs to the whole axis, not to a category (``start == end == 0`` by
    convention). ``lower`` and ``upper`` are the data values it removes from the scale; both
    ``None`` means automatic (see ``core/axis_break.py``).
    """

    kind: AnnotationKind
    start: int
    end: int
    series: int | None = None
    style: ArrowStyle = "bracket"
    label: LabelMode = "percent"
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in get_args(AnnotationKind):
            raise ValueError(f"unknown annotation kind: {self.kind!r}")
        if self.style not in get_args(ArrowStyle):
            raise ValueError(f"unknown arrow style: {self.style!r}")
        if self.label not in get_args(LabelMode):
            raise ValueError(f"unknown label mode: {self.label!r}")
        if min(self.start, self.end, 0 if self.series is None else self.series) < 0:
            raise ValueError("annotation indices must not be negative")
        if self.kind == "axis_break":
            if self.end != self.start:
                raise ValueError("an axis break belongs to the axis, not to categories")
        elif self.end == self.start:
            raise ValueError("an arrow needs two different categories")
        if (self.lower is None) != (self.upper is None):
            raise ValueError("an axis break needs both values or neither")
        if self.lower is not None and self.upper is not None:
            if self.kind != "axis_break":
                raise ValueError("only an axis break has a value range")
            if not (math.isfinite(self.lower) and math.isfinite(self.upper)):
                raise ValueError("the range of an axis break must be finite")
            if not 0 <= self.lower < self.upper:
                raise ValueError("an axis break needs 0 <= lower < upper")


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
