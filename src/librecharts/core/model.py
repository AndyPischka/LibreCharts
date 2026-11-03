"""Chart state: the persisted, UNO-free description of one chart."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, get_args

SCHEMA_VERSION = 13

ChartKind = Literal[
    "column", "bar", "waterfall", "mekko", "line", "area", "pie", "scatter", "butterfly", "gantt"
]
Grouping = Literal["stacked", "clustered"]
SortOrder = Literal["none", "descending", "ascending"]
AnnotationKind = Literal[
    "difference", "cagr", "axis_break", "value_line", "category_gap", "group_bracket"
]
ArrowStyle = Literal["bracket", "level"]
LabelMode = Literal["percent", "absolute"]
SeriesNames = Literal["none", "labels", "legend"]
Magnitude = Literal[0, 3, 6, 9]
Separator = Literal[".", ","]
LabelRole = Literal["value", "total"]

AXIS_ANNOTATIONS = frozenset({"axis_break", "value_line"})


@dataclass(frozen=True, slots=True)
class Format:
    """How a chart shows values, axes and series names (ADR 0014).

    ``decimals`` is ``None`` for the automatic rule ("integers plain, at most two decimals").
    ``magnitude`` divides every value by a power of ten before formatting (3: thousands, 6:
    millions, 9: billions); ``unit`` is appended after it. ``separator`` and ``language`` are
    stored per chart, so a German deck keeps its decimal comma and German magnitude suffixes on an
    English machine. Format is the unit "copy chart format" copies between charts.
    """

    axis: bool = False
    gridlines: bool = False  # only drawn together with ``axis``
    series_names: SeriesNames = "none"
    decimals: int | None = None
    magnitude: Magnitude = 0
    unit: str = ""
    separator: Separator = "."
    language: str = "en"
    markers: bool = True  # point markers on line series

    def __post_init__(self) -> None:
        if self.series_names not in get_args(SeriesNames):
            raise ValueError(f"unknown series name mode: {self.series_names!r}")
        if not isinstance(self.markers, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("markers must be true or false")
        if self.decimals is not None and not 0 <= self.decimals <= 4:
            raise ValueError("decimals must be None or between 0 and 4")
        if self.magnitude not in (0, 3, 6, 9):
            raise ValueError("magnitude must be 0, 3, 6 or 9")
        if len(self.unit) > 10:
            raise ValueError("the unit must be at most 10 characters")
        if self.separator not in (".", ","):
            raise ValueError(f"unknown decimal separator: {self.separator!r}")
        if len(self.language) != 2 or not self.language.isalpha():
            raise ValueError(f"language must be a two-letter code, not {self.language!r}")


@dataclass(frozen=True, slots=True)
class Annotation:
    """An arrow, axis break, value line, category gap or group bracket on a chart.

    ``start`` and ``end`` are category indices. ``series`` is ``None`` for a column total and a
    series index for one bar of a clustered chart; ``series_end`` is the series the *end* value
    comes from: ``None`` means the same series as ``series`` (M14: a between-series arrow has a
    different ``series_end``). ``style`` and ``label`` only matter for difference arrows.
    Indices are not checked against the data: after a data sheet edit an annotation may point
    past the last category, it is then not drawn.

    An axis break and a value line belong to the whole axis, not to a category (``start == end ==
    0`` by convention). ``lower`` and ``upper`` are the values an axis break removes from the
    scale; both ``None`` means automatic (see ``core/axis_break.py``). A value line's ``value`` is
    the horizontal/vertical level it marks; ``None`` means the average (see ``core/value_line.py``).

    A ``category_gap`` opens between the adjacent categories ``start`` and ``end``
    (``end == start + 1``); it is drawn only while they stay adjacent in display order. A
    ``group_bracket`` spans the categories ``start..end`` and carries its label in ``text``
    (empty: no label). Both belong to whole categories, not to one series.
    """

    kind: AnnotationKind
    start: int
    end: int
    series: int | None = None
    style: ArrowStyle = "bracket"
    label: LabelMode = "percent"
    lower: float | None = None
    upper: float | None = None
    value: float | None = None
    series_end: int | None = None
    text: str = ""

    def __post_init__(self) -> None:
        if self.kind not in get_args(AnnotationKind):
            raise ValueError(f"unknown annotation kind: {self.kind!r}")
        if self.style not in get_args(ArrowStyle):
            raise ValueError(f"unknown arrow style: {self.style!r}")
        if self.label not in get_args(LabelMode):
            raise ValueError(f"unknown label mode: {self.label!r}")
        if (
            min(
                self.start,
                self.end,
                0 if self.series is None else self.series,
                0 if self.series_end is None else self.series_end,
            )
            < 0
        ):
            raise ValueError("annotation indices must not be negative")
        if self.series is None and self.series_end is not None:
            raise ValueError("only an arrow with a start series can have an end series")
        if self.kind in AXIS_ANNOTATIONS:
            if self.start != 0 or self.end != 0:
                raise ValueError("this annotation belongs to the axis, not to categories")
            if self.series is not None:
                raise ValueError("this annotation belongs to the whole axis, not to one series")
        elif self.kind == "category_gap":
            if self.series is not None:
                raise ValueError("a category gap belongs to the whole category, not to one series")
            if self.end != self.start + 1:
                raise ValueError("a category gap opens between two adjacent categories")
        elif self.kind == "group_bracket":
            if self.series is not None:
                raise ValueError("a group bracket spans whole categories, not one series")
            if self.end <= self.start:
                raise ValueError("a group bracket spans at least two categories")
        elif self.end == self.start and (
            self.series is None or self.series_end in (None, self.series)
        ):
            raise ValueError("an arrow needs two different categories or two different series")
        if (self.lower is None) != (self.upper is None):
            raise ValueError("an axis break needs both values or neither")
        if self.lower is not None and self.upper is not None:
            if self.kind != "axis_break":
                raise ValueError("only an axis break has a value range")
            if not (math.isfinite(self.lower) and math.isfinite(self.upper)):
                raise ValueError("the range of an axis break must be finite")
            if not 0 <= self.lower < self.upper:
                raise ValueError("an axis break needs 0 <= lower < upper")
        if self.value is not None:
            if self.kind != "value_line":
                raise ValueError("only a value line has a value")
            if not math.isfinite(self.value):
                raise ValueError("the value of a value line must be finite")
        if self.text and self.kind != "group_bracket":
            raise ValueError("only a group bracket has a text")
        if len(self.text) > 80:
            raise ValueError("the bracket label must be at most 80 characters")


@dataclass(frozen=True, slots=True)
class LabelKey:
    """Names a movable label by its role and data sheet indices, independently of size and order.

    ``category`` and ``series`` are indices into ``ChartData`` (``series`` is ``None`` where a
    label belongs to a category or row alone: a total, a waterfall step, a scatter point). The role
    keeps a total apart from a value label that has the same indices.
    """

    role: LabelRole
    category: int
    series: int | None = None

    def __post_init__(self) -> None:
        if self.role not in get_args(LabelRole):
            raise ValueError(f"unknown label role: {self.role!r}")
        if min(self.category, 0 if self.series is None else self.series) < 0:
            raise ValueError("label indices must not be negative")


@dataclass(frozen=True, slots=True)
class LabelOffset:
    """How far the user moved a label's centre from where the layout puts it, in 1/100 mm.

    Absolute: not scaled when the chart is resized, like font sizes (ADR 0023).
    """

    key: LabelKey
    dx: float
    dy: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.dx) and math.isfinite(self.dy)):
            raise ValueError("a label offset must be finite")


@dataclass(frozen=True, slots=True)
class Link:
    """Where a linked chart takes its data from: a range of an external spreadsheet (ADR 0020).

    ``url`` is the source's absolute URL; ``relative`` the same file relative to the presentation
    (empty if the two have no common root or the presentation was never saved), so a folder with
    deck and workbook can be moved. ``sheet`` and ``range`` name an address such as ``B2:F6``;
    an empty ``sheet`` makes ``range`` the name of a named range. ``updated`` is the local time of
    the last update (display only) and ``modified`` the source's modification time read then,
    which tells whether the source changed since. Neither is ever used by the layout.
    """

    url: str
    sheet: str
    range: str
    relative: str = ""
    updated: str = ""
    modified: str = ""

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("a data link needs the URL of its source")
        if not self.range.strip():
            raise ValueError("a data link needs a range or a name")


@dataclass(frozen=True, slots=True)
class ChartState:
    """Everything needed to redraw and re-edit a chart.

    ``cells`` holds the raw data sheet contents as Calc returns them (numbers, text and formulas
    such as ``=B2*2``). ``values`` holds the evaluated numbers the chart is drawn from, ``None``
    where a cell is empty or not numeric. Both grids are rectangular and have the same shape.

    ``percent`` draws a 100 % chart: a Mekko with every column 100 % high, or a stacked column,
    bar or area chart whose segments show shares of their column. ``sort`` reorders the categories
    of a column or bar chart for display only, without touching the data sheet. Neither has a
    meaning for the other chart kinds, where they keep their defaults. ``format`` holds axis,
    number and series-name options.

    ``lines`` holds the series of a column chart that are drawn as lines instead of columns;
    ``secondary`` is the subset of them on the right-hand axis. Series indices are data sheet rows,
    like annotation indices: after a data edit a dangling index is ignored.

    ``colors`` overrides the palette entry of single series (``None``: the default entry of that
    series), indexed like annotation series indices: after a data edit a dangling index is ignored.
    ``scale_group`` ties charts together so that they draw the same value with the same length
    (ADR 0017); ``None`` is the chart's own scale.

    ``doughnut`` turns a pie chart into a doughnut chart (ADR 0018). A pie chart draws one pie per
    category; a scatter chart reads its data sheet by column position (``core/scatter.py``) and a
    butterfly chart draws the first two series as mirrored bars. A Gantt chart reads its data sheet
    by column position too (``core/gantt.py``); its only sort order besides ``"none"`` is
    ``"ascending"``, by start date. ``grouping`` has no meaning for these four and stays
    ``"stacked"``.

    ``link`` takes the data from an external spreadsheet instead of the data sheet (ADR 0020). The
    fetched values are stored in ``cells`` and ``values`` like data sheet values, so the chart draws
    without its source.

    ``labels`` holds the offsets of value labels and totals the user moved by hand, at most one per
    label. Like annotation indices they refer to data sheet indices: sorting never touches them, and
    an offset whose label is gone stays stored and unused.
    """

    kind: ChartKind
    grouping: Grouping
    cells: tuple[tuple[str, ...], ...]
    values: tuple[tuple[float | None, ...], ...]
    annotations: tuple[Annotation, ...] = ()
    percent: bool = False
    sort: SortOrder = "none"
    format: Format = Format()
    lines: tuple[int, ...] = ()
    secondary: tuple[int, ...] = ()
    colors: tuple[int | None, ...] = ()
    scale_group: str | None = None
    doughnut: bool = False
    link: Link | None = None
    labels: tuple[LabelOffset, ...] = ()
    version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.kind not in get_args(ChartKind):
            raise ValueError(f"unknown chart kind: {self.kind!r}")
        if self.grouping not in get_args(Grouping):
            raise ValueError(f"unknown grouping: {self.grouping!r}")
        if self.sort not in get_args(SortOrder):
            raise ValueError(f"unknown sort order: {self.sort!r}")
        if self.percent and not (
            self.kind == "mekko"
            or (self.kind in ("column", "bar", "area") and self.grouping == "stacked")
        ):
            raise ValueError(
                "only a Marimekko chart or a stacked column, bar or area chart can be a "
                "percent chart"
            )
        if self.kind in ("line", "area") and self.grouping != "stacked":
            raise ValueError(f"a {self.kind} chart is always stacked")
        if self.sort != "none" and self.kind not in ("column", "bar", "butterfly", "gantt"):
            raise ValueError(f"a {self.kind} chart cannot be sorted")
        if self.kind == "gantt" and self.sort == "descending":
            raise ValueError("a Gantt chart sorts by ascending start date only")
        if self.doughnut and self.kind != "pie":
            raise ValueError("only a pie chart can be a doughnut chart")
        if (self.lines or self.secondary) and self.kind != "column":
            raise ValueError("only a column chart can draw series as lines")
        if self.lines and self.percent:
            raise ValueError("a 100 % chart cannot draw series as lines")
        if len(set(self.lines)) != len(self.lines) or len(set(self.secondary)) != len(
            self.secondary
        ):
            raise ValueError("series indices must be unique")
        if any(index < 0 for index in (*self.lines, *self.secondary)):
            raise ValueError("series indices must not be negative")
        if not set(self.secondary) <= set(self.lines):
            raise ValueError("the series on the secondary axis must be lines")
        if any(colour is not None and colour < 0 for colour in self.colors):
            raise ValueError("palette indices must not be negative")
        if self.scale_group is not None and not self.scale_group.strip():
            raise ValueError("a scale group needs a non-empty id")
        if len(self.cells) != len(self.values):
            raise ValueError("cells and values must have the same number of rows")
        widths = {len(row) for row in (*self.cells, *self.values)}
        if len(widths) > 1:
            raise ValueError("cells and values must be rectangular and of equal width")
        if any(v is not None and not math.isfinite(v) for row in self.values for v in row):
            raise ValueError("values must be finite numbers or None")
        if len({offset.key for offset in self.labels}) != len(self.labels):
            raise ValueError("a label can only have one offset")
