"""Layout of stacked and clustered column charts.

The kinds and order of the returned primitives depend only on the data, never on the size.

No value axis is drawn (like think-cell): values are labelled directly. The axis range only
fixes the scale and always includes zero. Above the plot there is a band for total and value
labels, below it a band for category labels. Bracket arrows (difference, CAGR) run in lanes
above the label band, one lane per arrow, the first one closest to the plot. Level arrows run in
lanes right of the plot, the first one closest to it.

An axis break shortens a column that dwarfs the others: the scale ignores it, and it is drawn
just above the tallest other column with a break mark; its labels keep the real values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import GAP_RATIO, format_value, value_axis
from librecharts.core.model import Annotation, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, nice_axis

TOP_BAND = 800.0  # room above the plot for total / outside value labels
LABEL_HEIGHT = 600.0  # height of a value or total label box
CATEGORY_BAND = 1000.0  # room below the plot for category names
MIN_SEGMENT_FOR_LABEL = 500.0  # segments flatter than this get no inside label
LANE_HEIGHT = 800.0  # room for one arrow above the plot: its label and line
LANE_LINE_GAP = 100.0  # between an arrow's line and the bottom of its lane, or a column's label
MIN_ARROW_LABEL_WIDTH = 1800.0  # arrows between neighbouring narrow columns stay readable
LEVEL_LANE_WIDTH = 2000.0  # room right of the plot for one level arrow and its label
LEVEL_ARROW_INSET = 300.0  # from a level lane's left edge to its arrow
LEVEL_LABEL_GAP = 150.0  # between a level arrow and its label
BREAK_KEEP = 0.85  # below its break, a cut column keeps this share of the tallest other column
BREAK_SHOW = 1.15  # a cut column ends this high, relative to the tallest other column
BREAK_GAP = 300.0  # height of the white gap of a break mark
BREAK_SLANT = 100.0  # how far the break lines fall from left to right
BREAK_OVERHANG = 100.0  # how far a break mark reaches beyond a stacked column

_YScale = Callable[[float], float]


def layout_column(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    brackets, levels = _arrows(data, annotations)
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes + TOP_BAND
    plot_width = width - len(levels) * LEVEL_LANE_WIDTH
    plot_height = height - top_band - CATEGORY_BAND
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    # Labels of negative columns hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    cut = _cut(data, grouping, annotations)
    axis = _axis(data, grouping, cut)
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        return top_band + (axis.maximum - value) / span * scale_height

    slot = plot_width / len(data.categories)
    column_width = slot * (1 - GAP_RATIO)
    out: list[Primitive] = [Line(0, y(0), plot_width, y(0), "baseline")]

    for c, category in enumerate(data.categories):
        slot_x = c * slot
        column_x = slot_x + (slot - column_width) / 2
        if grouping == "stacked":
            out.extend(_stacked_column(data, c, column_x, column_width, y, cut))
        else:
            out.extend(_clustered_column(data, c, column_x, column_width, y, cut))
        out.append(
            Text(
                slot_x, top_band + plot_height, slot, CATEGORY_BAND, category, "center", "category"
            )
        )

    def edges(category: int, series: int | None) -> tuple[float, float]:
        """Left and right edge of the measured column, or of one bar of a clustered column."""
        column_x = category * slot + (slot - column_width) / 2
        if series is not None and grouping == "clustered":
            bar_width = column_width / len(data.series)
            return column_x + series * bar_width, column_x + (series + 1) * bar_width
        return column_x, column_x + column_width

    def top(category: int, series: int | None) -> float:
        """The highest value of the measured column or bar (0 if it only goes down)."""
        values = [v for s in data.series if (v := s.values[category]) is not None]
        if series is not None and grouping == "clustered":
            return max(data.series[series].values[category] or 0.0, 0.0)
        if grouping == "clustered":
            return max([0.0, *values])
        return sum(v for v in values if v > 0)

    def drawn(category: int, series: int | None, value: float) -> float:
        """The y of ``value`` on the measured column or bar, which may be cut."""
        fold = cut.fold(category, top(category, series)) if cut else _same
        return y(fold(value))

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets a column: top centre, above its label."""
        left, right = edges(category, series)
        y_top = drawn(category, series, top(category, series))
        return (left + right) / 2, y_top - LABEL_HEIGHT - LANE_LINE_GAP

    def level(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge, at the measured value."""
        value = notes.measured_value(data, category, series) or 0.0
        return edges(category, series)[1], drawn(category, series, value)

    for lane, arrow in enumerate(brackets):
        line_y = lanes - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            _bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, arrow.series),
                line_y,
                notes.label(arrow, data),
            )
        )
    for lane, arrow in enumerate(levels):
        arrow_x = plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            _level(
                level(arrow.start, arrow.series),
                level(arrow.end, arrow.series),
                arrow_x,
                notes.label(arrow, data),
            )
        )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class _Cut:
    """Axis breaks: a column (stacked) or bar (clustered) in ``categories`` reaching above
    ``show`` is cut at ``keep`` and ends at ``show``."""

    categories: frozenset[int]
    keep: float
    show: float

    def cuts(self, category: int, top: float) -> bool:
        return category in self.categories and top > self.show

    def fold(self, category: int, top: float) -> Callable[[float], float]:
        """Maps a value on a column or bar reaching ``top`` to the value it is drawn at."""
        if not self.cuts(category, top):
            return _same
        removed = top - self.show
        return lambda value: value if value <= self.keep else max(self.keep, value - removed)


def _same(value: float) -> float:
    return value


def _top(data: ChartData, grouping: Grouping, category: int) -> float:
    values = [v for s in data.series if (v := s.values[category]) is not None]
    if grouping == "clustered":
        return max([0.0, *values])
    return sum(v for v in values if v > 0)


def _cut(data: ChartData, grouping: Grouping, annotations: tuple[Annotation, ...]) -> _Cut | None:
    """The axis breaks to draw, sized by the tallest column without one."""
    categories = frozenset(
        a.start for a in annotations if a.kind == "axis_break" and notes.drawable(a, data, "column")
    )
    others = [_top(data, grouping, c) for c in range(len(data.categories)) if c not in categories]
    tallest = max(others, default=0.0)
    if not categories or tallest <= 0:
        return None
    return _Cut(categories, BREAK_KEEP * tallest, BREAK_SHOW * tallest)


def _axis(data: ChartData, grouping: Grouping, cut: _Cut | None) -> Axis:
    """Like ``value_axis``, but cut columns only count up to where they end."""
    if cut is None:
        return value_axis(data, grouping)
    lows: list[float] = []
    highs: list[float] = []
    for c in range(len(data.categories)):
        values = [v for s in data.series if (v := s.values[c]) is not None]
        negative = [v for v in values if v < 0]
        lows.append(sum(negative) if grouping == "stacked" else min(negative, default=0.0))
        high = _top(data, grouping, c)
        highs.append(min(high, cut.show) if c in cut.categories else high)
    return nice_axis(min(lows), max(highs))


def _break_mark(x: float, width: float, y_break: float, overhang: float) -> list[Primitive]:
    """A white gap across a column or bar with two parallel slanted lines."""
    left, right, top = x - overhang, x + width + overhang, y_break - BREAK_GAP / 2
    return [
        Rect(left, top, right - left, BREAK_GAP, BACKGROUND),
        Line(left, top, right, top + BREAK_SLANT, "annotation"),
        Line(left, top + BREAK_GAP - BREAK_SLANT, right, top + BREAK_GAP, "annotation"),
    ]


def _arrows(
    data: ChartData, annotations: tuple[Annotation, ...]
) -> tuple[list[Annotation], list[Annotation]]:
    """The drawable arrows: (bracket arrows above the plot, level arrows right of it)."""
    shown = [a for a in annotations if a.kind != "axis_break" and notes.drawable(a, data, "column")]
    levels = [a for a in shown if a.kind == "difference" and a.style == "level"]
    return [a for a in shown if a not in levels], levels


def column_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
) -> tuple[int, int | None] | None:
    """The category (and, for a bar of a clustered chart, the series) at chart point (x, y).

    Uses the geometry of :func:`layout_column`. Points in the arrow lanes or outside the box hit
    nothing; between the bars of a clustered column, or on its labels below, the series is ``None``.
    """
    brackets, levels = _arrows(data, annotations)
    plot_width = width - len(levels) * LEVEL_LANE_WIDTH
    if not data.categories or not 0 <= x < plot_width or y < len(brackets) * LANE_HEIGHT:
        return None
    slot = plot_width / len(data.categories)
    category = int(x // slot)
    if grouping == "stacked" or not data.series:
        return category, None
    column_width = slot * (1 - GAP_RATIO)
    offset = x - category * slot - (slot - column_width) / 2
    if not 0 <= offset < column_width:
        return category, None
    return category, int(offset // (column_width / len(data.series)))


def _bracket(
    start: tuple[float, float], end: tuple[float, float], line_y: float, label: str
) -> list[Primitive]:
    """Up from ``start``, across at ``line_y``, down onto ``end`` with an arrowhead."""
    (x1, y1), (x2, y2) = start, end
    left, right = min(x1, x2), max(x1, x2)
    label_width = max(right - left, MIN_ARROW_LABEL_WIDTH)
    return [
        Line(x1, line_y, x1, y1, "annotation"),
        Line(left, line_y, right, line_y, "annotation"),
        Line(x2, line_y, x2, y2, "annotation", arrow=True),
        Text(
            (left + right - label_width) / 2,
            line_y - LABEL_HEIGHT,
            label_width,
            LABEL_HEIGHT,
            label,
            "center",
            "annotation",
        ),
    ]


def _level(
    start: tuple[float, float], end: tuple[float, float], arrow_x: float, label: str
) -> list[Primitive]:
    """Dashed lines from both levels to ``arrow_x``, an arrow from one level to the other."""
    (x1, y1), (x2, y2) = start, end
    return [
        Line(x1, y1, arrow_x, y1, "helper"),
        Line(x2, y2, arrow_x, y2, "helper"),
        Line(arrow_x, y1, arrow_x, y2, "annotation", arrow=True),
        Text(
            arrow_x + LEVEL_LABEL_GAP,
            (y1 + y2 - LABEL_HEIGHT) / 2,
            LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
            LABEL_HEIGHT,
            label,
            "left",
            "annotation",
        ),
    ]


def _stacked_column(
    data: ChartData, c: int, x: float, width: float, y: _YScale, cut: _Cut | None
) -> list[Primitive]:
    out: list[Primitive] = []
    column_top = _top(data, "stacked", c)
    fold = cut.fold(c, column_top) if cut else _same
    positive = negative = 0.0
    segments = 0
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None or value == 0:
            continue
        segments += 1
        if value > 0:
            top, bottom = y(fold(positive + value)), y(fold(positive))
            positive += value
        else:
            top, bottom = y(negative), y(negative + value)
            negative += value
        out.append(Rect(x, top, width, bottom - top, i))
        # Always emit the label (empty if the segment is too flat): the primitive structure must
        # not depend on the size, so a resized chart can be re-laid out in place (lo/render.py).
        label = format_value(value) if bottom - top >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(x, top, width, bottom - top, label, "center", "value"))
    if segments >= 2:  # a single segment's total would just repeat its own label
        out.append(
            Text(
                x,
                y(fold(positive)) - LABEL_HEIGHT,
                width,
                LABEL_HEIGHT,
                format_value(positive + negative),
                "center",
                "total",
            )
        )
    if cut and cut.cuts(c, column_top):
        out.extend(_break_mark(x, width, y(cut.keep), BREAK_OVERHANG))
    return out


def _clustered_column(
    data: ChartData, c: int, x: float, width: float, y: _YScale, cut: _Cut | None
) -> list[Primitive]:
    out: list[Primitive] = []
    bar_width = width / len(data.series)
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_x = x + i * bar_width
        fold = cut.fold(c, value) if cut else _same
        top, bottom = (y(fold(value)), y(0)) if value >= 0 else (y(0), y(value))
        out.append(Rect(bar_x, top, bar_width, bottom - top, i))
        label_y = top - LABEL_HEIGHT if value >= 0 else bottom
        out.append(
            Text(bar_x, label_y, bar_width, LABEL_HEIGHT, format_value(value), "center", "value")
        )
        if cut and cut.cuts(c, value):  # bars sit side by side: the mark stays on its bar
            out.extend(_break_mark(bar_x, bar_width, y(cut.keep), 0.0))
    return out
