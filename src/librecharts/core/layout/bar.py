"""Layout of stacked and clustered bar charts (horizontal columns).

Categories run top to bottom in data order, values left to right. As in the column layout no value
axis is drawn and the kinds and order of the primitives depend only on the data, never on the size.
Category names sit in a band on the left, outside labels (totals, clustered values) on the right
of the bars. Negative values grow to the left and their outside labels get extra room next to the
names.

Annotations are the column layout turned by 90 degrees: bracket arrows (difference, CAGR) run in
lanes right of the outside labels, one lane per arrow, the first one closest to the plot; level
arrows run in lanes below the plot. An axis break removes a value range from the scale
(core/axis_break.py): bars reaching beyond it get a vertical break mark.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core.axis_break import Break, column_tops, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.column import (
    BREAK_GAP,
    BREAK_OVERHANG,
    BREAK_SLANT,
    MIN_ARROW_LABEL_WIDTH,
)
from librecharts.core.layout.common import GAP_RATIO, column_top, format_value, value_axis
from librecharts.core.model import Annotation, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text

LEFT_BAND = 3000.0  # room left of the plot for category names
RIGHT_BAND = 1200.0  # room right of the plot for outside labels of positive values and totals
LABEL_WIDTH = 1200.0  # width of an outside value or total label box (incl. LABEL_GAP)
LABEL_HEIGHT = 600.0
LABEL_GAP = 150.0  # between a bar end and its outside label, and before the category names
MIN_SEGMENT_FOR_LABEL = 800.0  # segments narrower than this get no inside label
ANCHOR_GAP = 100.0  # between a bar's outside label and the line of a bracket arrow
BRACKET_LANE_WIDTH = 2200.0  # room right of the plot for one bracket arrow and its label
BRACKET_INSET = 300.0  # from a bracket lane's left edge to its vertical line
BRACKET_LABEL_GAP = 150.0  # between a bracket arrow's vertical line and its label
LEVEL_LANE_HEIGHT = 1100.0  # room below the plot for one level arrow and its label
LEVEL_ARROW_INSET = 200.0  # from a level lane's top edge to its arrow
LEVEL_LABEL_GAP = 100.0  # between a level arrow and its label

_XScale = Callable[[float], float]


def layout_bar(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    brackets, levels = notes.arrows(annotations, data, "bar")
    plot_left, plot_width, plot_height = _plot(data, width, height, len(brackets), len(levels))
    if plot_height <= 0 or plot_width <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    cut = resolve(annotations, data, grouping)
    axis = shortened_axis(data, grouping, cut) if cut else value_axis(data, grouping)
    span = axis.maximum - axis.minimum
    fold = cut.fold if cut else _same

    def x(value: float) -> float:
        return plot_left + (fold(value) - axis.minimum) / span * plot_width

    slot = plot_height / len(data.categories)
    thickness = slot * (1 - GAP_RATIO)
    out: list[Primitive] = [Line(x(0), 0, x(0), plot_height, "baseline")]

    for c, category in enumerate(data.categories):
        slot_y = c * slot
        bar_y = slot_y + (slot - thickness) / 2
        if grouping == "stacked":
            out.extend(_stacked_bar(data, c, bar_y, thickness, x, cut))
        else:
            out.extend(_clustered_bar(data, c, bar_y, thickness, x, cut))
        out.append(
            Text(0, slot_y, LEFT_BAND - LABEL_GAP, slot, category, "right", "category"),
        )

    def edges(category: int, series: int | None) -> tuple[float, float]:
        """Top and bottom edge of the measured bar, or of one bar of a clustered chart."""
        bar_y = category * slot + (slot - thickness) / 2
        if series is not None and grouping == "clustered":
            bar_height = thickness / len(data.series)
            return bar_y + series * bar_height, bar_y + (series + 1) * bar_height
        return bar_y, bar_y + thickness

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets a bar: right of its outside label, at mid-height."""
        top, bottom = edges(category, series)
        end = x(column_top(data, grouping, category, series))
        return end + LABEL_WIDTH + ANCHOR_GAP, (top + bottom) / 2

    def level(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: bottom edge, at the measured value."""
        value = notes.measured_value(data, category, series) or 0.0
        return x(value), edges(category, series)[1]

    lane_start = plot_left + plot_width + RIGHT_BAND
    for lane, arrow in enumerate(brackets):
        out.extend(
            _bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, arrow.series),
                lane_start + lane * BRACKET_LANE_WIDTH + BRACKET_INSET,
                notes.label(arrow, data),
            )
        )
    for lane, arrow in enumerate(levels):
        out.extend(
            _level(
                level(arrow.start, arrow.series),
                level(arrow.end, arrow.series),
                plot_height + lane * LEVEL_LANE_HEIGHT + LEVEL_ARROW_INSET,
                notes.label(arrow, data),
            )
        )
    return tuple(out)


def _same(value: float) -> float:
    return value


def _plot(
    data: ChartData, width: float, height: float, brackets: int, levels: int
) -> tuple[float, float, float]:
    """Left edge, width and height of the plot area."""
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    # Labels of negative bars hang to the left of them and must not run into the category names.
    plot_left = LEFT_BAND + (LABEL_WIDTH if has_negative else 0.0)
    plot_width = width - plot_left - RIGHT_BAND - brackets * BRACKET_LANE_WIDTH
    return plot_left, plot_width, height - levels * LEVEL_LANE_HEIGHT


def bar_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
) -> tuple[int, int | None] | None:
    """The category (and, for a bar of a clustered chart, the series) at chart point (x, y).

    Uses the geometry of :func:`layout_bar`. Points in the arrow lanes or outside the box hit
    nothing; between the bars of a clustered category the series is ``None``.
    """
    brackets, levels = notes.arrows(annotations, data, "bar")
    plot_left, plot_width, plot_height = _plot(data, width, height, len(brackets), len(levels))
    if not data.categories or plot_width <= 0 or plot_height <= 0:
        return None
    if not 0 <= x < plot_left + plot_width + RIGHT_BAND or not 0 <= y < plot_height:
        return None
    slot = plot_height / len(data.categories)
    category = int(y // slot)
    if grouping == "stacked" or not data.series:
        return category, None
    thickness = slot * (1 - GAP_RATIO)
    offset = y - category * slot - (slot - thickness) / 2
    if not 0 <= offset < thickness:
        return category, None
    return category, int(offset // (thickness / len(data.series)))


def _bracket(
    start: tuple[float, float], end: tuple[float, float], lane_x: float, label: str
) -> list[Primitive]:
    """Out from ``start`` to ``lane_x``, along it, back onto ``end`` with an arrowhead."""
    (x1, y1), (x2, y2) = start, end
    return [
        Line(x1, y1, lane_x, y1, "annotation"),
        Line(lane_x, y1, lane_x, y2, "annotation"),
        Line(lane_x, y2, x2, y2, "annotation", arrow=True),
        Text(
            lane_x + BRACKET_LABEL_GAP,
            (y1 + y2 - LABEL_HEIGHT) / 2,
            BRACKET_LANE_WIDTH - BRACKET_INSET - BRACKET_LABEL_GAP,
            LABEL_HEIGHT,
            label,
            "left",
            "annotation",
        ),
    ]


def _level(
    start: tuple[float, float], end: tuple[float, float], arrow_y: float, label: str
) -> list[Primitive]:
    """Dashed lines from both levels down to ``arrow_y``, an arrow from one level to the other."""
    (x1, y1), (x2, y2) = start, end
    label_width = max(abs(x2 - x1), MIN_ARROW_LABEL_WIDTH)
    return [
        Line(x1, y1, x1, arrow_y, "helper"),
        Line(x2, y2, x2, arrow_y, "helper"),
        Line(x1, arrow_y, x2, arrow_y, "annotation", arrow=True),
        Text(
            (x1 + x2 - label_width) / 2,
            arrow_y + LEVEL_LABEL_GAP,
            label_width,
            LABEL_HEIGHT,
            label,
            "center",
            "annotation",
        ),
    ]


def _break_mark(x: float, y: float, thickness: float, overhang: float) -> list[Primitive]:
    """A white vertical gap across a bar at ``x`` with two parallel slanted lines."""
    left, top, bottom = x - BREAK_GAP / 2, y - overhang, y + thickness + overhang
    return [
        Rect(left, top, BREAK_GAP, bottom - top, BACKGROUND),
        Line(left, top, left + BREAK_SLANT, bottom, "annotation"),
        Line(left + BREAK_GAP - BREAK_SLANT, top, left + BREAK_GAP, bottom, "annotation"),
    ]


def _stacked_bar(
    data: ChartData, c: int, y: float, thickness: float, x: _XScale, cut: Break | None
) -> list[Primitive]:
    out: list[Primitive] = []
    positive = negative = 0.0
    segments = 0
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None or value == 0:
            continue
        segments += 1
        if value > 0:
            left, right = x(positive), x(positive + value)
            positive += value
        else:
            left, right = x(negative + value), x(negative)
            negative += value
        out.append(Rect(left, y, right - left, thickness, i))
        # Always emit the label (empty if the segment is too narrow): the structure must not depend
        # on the size, so a resized chart can be re-laid out in place (lo/render.py).
        label = format_value(value) if right - left >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(left, y, right - left, thickness, label, "center", "value"))
    if segments >= 2:  # a single segment's total would just repeat its own label
        out.append(
            Text(
                x(positive) + LABEL_GAP,
                y + (thickness - LABEL_HEIGHT) / 2,
                LABEL_WIDTH - LABEL_GAP,
                LABEL_HEIGHT,
                format_value(positive + negative),
                "left",
                "total",
            )
        )
    if cut and cut.cuts(column_tops(data, "stacked")[c]):
        out.extend(_break_mark(x(cut.lower), y, thickness, BREAK_OVERHANG))
    return out


def _clustered_bar(
    data: ChartData, c: int, y: float, thickness: float, x: _XScale, cut: Break | None
) -> list[Primitive]:
    out: list[Primitive] = []
    bar_height = thickness / len(data.series)
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_y = y + i * bar_height
        label_y = bar_y + (bar_height - LABEL_HEIGHT) / 2
        text = format_value(value)
        if value >= 0:
            left, right = x(0), x(value)
            label = Text(
                right + LABEL_GAP,
                label_y,
                LABEL_WIDTH - LABEL_GAP,
                LABEL_HEIGHT,
                text,
                "left",
                "value",
            )
        else:
            left, right = x(value), x(0)
            label = Text(
                left - LABEL_WIDTH,
                label_y,
                LABEL_WIDTH - LABEL_GAP,
                LABEL_HEIGHT,
                text,
                "right",
                "value",
            )
        out.append(Rect(left, bar_y, right - left, bar_height, i))
        out.append(label)
        if cut and cut.cuts(value):  # bars sit one below the other: the mark stays on its bar
            out.extend(_break_mark(x(cut.lower), bar_y, bar_height, 0.0))
    return out
