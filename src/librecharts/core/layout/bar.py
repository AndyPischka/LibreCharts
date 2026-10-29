"""Layout of stacked and clustered bar charts (horizontal columns).

Categories run top to bottom in data order, values left to right. As in the column layout no value
axis is drawn by default; the kinds and order of the primitives depend only on the data and the
format, never on the size. Category names sit in a band on the left, outside labels (totals,
clustered values) on the right of the bars. Negative values grow to the left and their outside
labels get extra room next to the names.

Annotations are the column layout turned by 90 degrees: bracket arrows (difference, CAGR) run in
lanes right of the outside labels, one lane per arrow, the first one closest to the plot; level
arrows and value lines run in lanes below the plot. An axis break removes a value range from the
scale (core/axis_break.py): bars reaching beyond it get a vertical break mark, ticks inside the
range are left out and the axis line gets a break mark.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.axis_break import Break, column_tops, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.column import (
    BREAK_GAP,
    BREAK_OVERHANG,
    BREAK_SLANT,
    MIN_ARROW_LABEL_WIDTH,
)
from librecharts.core.layout.common import (
    GAP_RATIO,
    LEGEND_HEIGHT,
    TICK_GAP,
    TICK_HEIGHT,
    column_top,
    format_value,
    legend,
    spread,
    value_axis,
    visible_ticks,
)
from librecharts.core.model import Annotation, Format, Grouping
from librecharts.core.percent import column_total, share_label
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis

PERCENT_AXIS = Axis(0.0, 100.0, 20.0)  # the fixed scale of a 100 % chart

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
SERIES_BAND = 2600.0  # room right of the lanes for series names
SERIES_LABEL_GAP = 150.0
AXIS_BAND_HEIGHT = 700.0  # room below the plot for tick labels
TICK_WIDTH = 1600.0  # width of one tick label box

_XScale = Callable[[float], float]


def layout_bar(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    percent: bool = False,
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``percent`` the bars are 100 % long and the segments show their share; such a chart has
    no annotations (they stay stored but are neither drawn nor offered).

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    if percent:
        brackets, levels, lines = [], [], []
    else:
        brackets, levels = notes.arrows(annotations, data, "bar")
        lines = notes.value_lines(annotations, data, "bar")
    plot_left, plot_top, plot_width, plot_height = _plot(
        data, width, height, len(brackets), len(levels) + len(lines), fmt, percent
    )
    if plot_height <= 0 or plot_width <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    cut = None if percent else resolve(annotations, data, grouping)
    axis = (
        PERCENT_AXIS
        if percent
        else (shortened_axis(data, grouping, cut) if cut else value_axis(data, grouping))
    )
    span = axis.maximum - axis.minimum
    fold = cut.fold if cut else _same

    def x(value: float) -> float:
        return plot_left + (fold(value) - axis.minimum) / span * plot_width

    slot = plot_height / len(data.categories)
    thickness = slot * (1 - GAP_RATIO)
    plot_bottom = plot_top + plot_height
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    out.append(Line(x(0), plot_top, x(0), plot_bottom, "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(_grid(axis, cut, x, plot_top, plot_bottom))
        out.extend(_axis(axis, cut, x, plot_bottom, fmt))

    for c, category in enumerate(data.categories):
        slot_y = plot_top + c * slot
        bar_y = slot_y + (slot - thickness) / 2
        if grouping == "stacked":
            out.extend(_stacked_bar(data, c, bar_y, thickness, x, cut, percent=percent, fmt=fmt))
        else:
            out.extend(_clustered_bar(data, c, bar_y, thickness, x, cut, fmt))
        out.append(
            Text(0, slot_y, LEFT_BAND - LABEL_GAP, slot, category, "right", "category"),
        )

    def edges(category: int, series: int | None) -> tuple[float, float]:
        """Top and bottom edge of the measured bar, or of one bar of a clustered chart."""
        bar_y = plot_top + category * slot + (slot - thickness) / 2
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
    lane_top = plot_bottom + (AXIS_BAND_HEIGHT if fmt.axis else 0.0)
    for lane, arrow in enumerate(levels):
        out.extend(
            _level(
                level(arrow.start, arrow.series),
                level(arrow.end, arrow.series),
                lane_top + lane * LEVEL_LANE_HEIGHT + LEVEL_ARROW_INSET,
                notes.label(arrow, data),
            )
        )
    for lane, annotation in enumerate(lines):
        out.extend(
            _value_line(
                annotation,
                data,
                x,
                fold,
                plot_top,
                plot_height,
                lane_top,
                len(levels) + lane,
                fmt,
            )
        )
    if fmt.series_names == "labels":
        out.extend(
            _series_names(
                data,
                grouping,
                thickness,
                plot_top,
                slot,
                lane_start + len(brackets) * BRACKET_LANE_WIDTH,
            )
        )
    return tuple(out)


def _same(value: float) -> float:
    return value


def _plot(
    data: ChartData,
    width: float,
    height: float,
    brackets: int,
    lanes: int,
    fmt: Format,
    percent: bool = False,
) -> tuple[float, float, float, float]:
    """Left edge, top edge, width and height of the plot area."""
    has_negative = not percent and any(
        v is not None and v < 0 for s in data.series for v in s.values
    )
    # Labels of negative bars hang to the left of them and must not run into the category names.
    plot_left = LEFT_BAND + (LABEL_WIDTH if has_negative else 0.0)
    plot_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - RIGHT_BAND - brackets * BRACKET_LANE_WIDTH - series_band
    axis_band = AXIS_BAND_HEIGHT if fmt.axis else 0.0
    plot_height = height - plot_top - axis_band - lanes * LEVEL_LANE_HEIGHT
    return plot_left, plot_top, plot_width, plot_height


def _axis(
    axis: Axis, cut: Break | None, x: _XScale, plot_bottom: float, fmt: Format
) -> list[Primitive]:
    """The horizontal axis line and tick labels below the plot."""
    out: list[Primitive] = [
        Line(x(axis.minimum), plot_bottom, x(axis.maximum), plot_bottom, "axis"),
    ]
    for tick in visible_ticks(axis, cut):
        left = x(cut.fold(tick) if cut else tick) - TICK_WIDTH / 2
        out.append(
            Text(
                left,
                plot_bottom + TICK_GAP,
                TICK_WIDTH,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "center",
                "axis",
            )
        )
    if cut:
        out.extend(_axis_break_mark(x(cut.lower), plot_bottom))
    return out


def _grid(
    axis: Axis, cut: Break | None, x: _XScale, plot_top: float, plot_bottom: float
) -> list[Primitive]:
    """Light vertical lines behind the bars, one per tick except zero (the baseline covers it)."""
    return [
        Line(
            x(cut.fold(tick) if cut else tick),
            plot_top,
            x(cut.fold(tick) if cut else tick),
            plot_bottom,
            "grid",
        )
        for tick in visible_ticks(axis, cut)
        if tick != 0
    ]


def _axis_break_mark(x_break: float, y: float) -> list[Primitive]:
    """A white gap and two slanted lines across the horizontal axis line."""
    left = x_break - BREAK_GAP / 2
    return [
        Rect(left, y - BREAK_GAP / 2, BREAK_GAP, BREAK_GAP, BACKGROUND),
        Line(left, y - BREAK_GAP / 2, left + BREAK_SLANT, y + BREAK_GAP / 2, "axis"),
        Line(
            left + BREAK_GAP - BREAK_SLANT,
            y - BREAK_GAP / 2,
            left + BREAK_GAP,
            y + BREAK_GAP / 2,
            "axis",
        ),
    ]


def _value_line(
    annotation: Annotation,
    data: ChartData,
    x: _XScale,
    fold: _XScale,
    plot_top: float,
    plot_height: float,
    lane_top: float,
    lane: int,
    fmt: Format,
) -> list[Primitive]:
    level = value_line.resolved(annotation, data)
    if level is None:
        return []
    line_x = x(fold(level))
    label_top = lane_top + lane * LEVEL_LANE_HEIGHT + LEVEL_LABEL_GAP
    return [
        Line(line_x, plot_top, line_x, plot_top + plot_height, "helper"),
        Text(
            line_x - TICK_WIDTH / 2,
            label_top,
            TICK_WIDTH,
            LABEL_HEIGHT,
            format_value(level, fmt),
            "center",
            "annotation",
        ),
    ]


def _series_names(
    data: ChartData,
    grouping: Grouping,
    thickness: float,
    plot_top: float,
    slot: float,
    band_x: float,
) -> list[Primitive]:
    """One series name per series, level with the last category's segments or bars."""
    last = len(data.categories) - 1
    labelled: list[tuple[float, str]] = []
    if grouping == "stacked":
        bar_y = plot_top + last * slot + (slot - thickness) / 2
        for series in data.series:
            labelled.append((bar_y + thickness / 2 - LABEL_HEIGHT / 2, series.name))
    else:
        bar_height = thickness / len(data.series)
        for i, series in enumerate(data.series):
            centre = plot_top + last * slot + (slot - thickness) / 2 + (i + 0.5) * bar_height
            labelled.append((centre - LABEL_HEIGHT / 2, series.name))
    labelled.sort(key=lambda item: item[0], reverse=True)
    tops = spread([top for top, _ in labelled], LABEL_HEIGHT)
    return [
        Text(
            band_x + SERIES_LABEL_GAP,
            top,
            SERIES_BAND - SERIES_LABEL_GAP,
            LABEL_HEIGHT,
            name,
            "left",
            "series",
        )
        for top, (_, name) in zip(tops, labelled, strict=True)
    ]


def bar_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format | None = None,
) -> tuple[int, int | None] | None:
    """The category (and, for a bar of a clustered chart, the series) at chart point (x, y).

    Uses the geometry of :func:`layout_bar`. Points in the arrow lanes or outside the box hit
    nothing; between the bars of a clustered category the series is ``None``.
    """
    fmt = fmt or Format()
    brackets, levels = notes.arrows(annotations, data, "bar")
    lines = notes.value_lines(annotations, data, "bar")
    plot_left, plot_top, plot_width, plot_height = _plot(
        data, width, height, len(brackets), len(levels) + len(lines), fmt
    )
    if not data.categories or plot_width <= 0 or plot_height <= 0:
        return None
    if not 0 <= x < plot_left + plot_width + RIGHT_BAND:
        return None
    if not plot_top <= y < plot_top + plot_height:
        return None
    slot = plot_height / len(data.categories)
    category = int((y - plot_top) // slot)
    if grouping == "stacked" or not data.series:
        return category, None
    thickness = slot * (1 - GAP_RATIO)
    offset = y - plot_top - category * slot - (slot - thickness) / 2
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
    data: ChartData,
    c: int,
    y: float,
    thickness: float,
    x: _XScale,
    cut: Break | None,
    *,
    percent: bool = False,
    fmt: Format,
) -> list[Primitive]:
    if percent:
        return _percent_bar(data, c, y, thickness, x, fmt)
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
        label = format_value(value, fmt) if right - left >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(left, y, right - left, thickness, label, "center", "value", fill=i))
    if segments >= 2:  # a single segment's total would just repeat its own label
        out.append(
            Text(
                x(positive) + LABEL_GAP,
                y + (thickness - LABEL_HEIGHT) / 2,
                LABEL_WIDTH - LABEL_GAP,
                LABEL_HEIGHT,
                format_value(positive + negative, fmt),
                "left",
                "total",
            )
        )
    if cut and cut.cuts(column_tops(data, "stacked")[c]):
        out.extend(_break_mark(x(cut.lower), y, thickness, BREAK_OVERHANG))
    return out


def _percent_bar(
    data: ChartData, c: int, y: float, thickness: float, x: _XScale, fmt: Format
) -> list[Primitive]:
    """A 100 % long bar: shares inside, the absolute column sum right of it."""
    total = column_total(data, c)
    if total <= 0:
        return []
    out: list[Primitive] = []
    level = 0.0
    for i, series in enumerate(data.series):
        value = series.values[c]
        percentage = share_label(value, total, fmt)
        if not percentage:
            continue
        length = (value or 0.0) / total * 100
        left, right = x(level), x(level + length)
        level += length
        out.append(Rect(left, y, right - left, thickness, i))
        # Always emit the label (empty if narrow): the structure must not depend on the size.
        label = percentage if right - left >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(left, y, right - left, thickness, label, "center", "value", fill=i))
    out.append(
        Text(
            x(100.0) + LABEL_GAP,
            y + (thickness - LABEL_HEIGHT) / 2,
            LABEL_WIDTH - LABEL_GAP,
            LABEL_HEIGHT,
            format_value(total, fmt),
            "left",
            "total",
        )
    )
    return out


def _clustered_bar(
    data: ChartData,
    c: int,
    y: float,
    thickness: float,
    x: _XScale,
    cut: Break | None,
    fmt: Format,
) -> list[Primitive]:
    out: list[Primitive] = []
    bar_height = thickness / len(data.series)
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_y = y + i * bar_height
        label_y = bar_y + (bar_height - LABEL_HEIGHT) / 2
        text = format_value(value, fmt)
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
