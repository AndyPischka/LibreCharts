"""Layout of stacked and clustered column charts.

The kinds and order of the returned primitives depend only on the data and the format, never on the
size.

No value axis is drawn by default (like think-cell): values are labelled directly. With
``Format.axis`` a band left of the plot carries tick labels and, with ``gridlines``, light lines
behind the columns. Above the plot there is a band for total and value labels (and the legend),
below it a band for category labels. Bracket arrows (difference, CAGR) run in lanes above the label
band, one lane per arrow, the first one closest to the plot. Level arrows and value lines run in
lanes right of the plot, the first one closest to it.

An axis break removes a value range from the scale of the whole axis (core/axis_break.py): columns
reaching beyond it get a break mark and continue above it; labels keep the real values, ticks inside
the removed range are left out and the axis line gets a break mark.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.axis_break import Break, column_tops, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    AXIS_BAND,
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
SERIES_BAND = 2600.0  # room right of the lanes for series names
SERIES_LABEL_GAP = 150.0  # between the lanes and a series name
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
    percent: bool = False,
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``percent`` the columns are 100 % high and the segments show their share; such a chart has
    no annotations (they stay stored but are neither drawn nor offered).

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    if percent:
        brackets, levels, lines = [], [], []
    else:
        brackets, levels = notes.arrows(annotations, data, "column")
        lines = notes.value_lines(annotations, data, "column")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes_top + lanes + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    right_lanes = len(levels) + len(lines)
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - right_lanes * LEVEL_LANE_WIDTH - series_band
    plot_height = height - top_band - CATEGORY_BAND
    has_negative = not percent and any(
        v is not None and v < 0 for s in data.series for v in s.values
    )
    # Labels of negative columns hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if plot_width <= 0 or scale_height <= 0:
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

    def y(value: float) -> float:
        return top_band + (axis.maximum - value) / span * scale_height

    fold = cut.fold if cut else _same
    slot = plot_width / len(data.categories)
    column_width = slot * (1 - GAP_RATIO)
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    out.append(Line(plot_left, y(0), plot_left + plot_width, y(0), "baseline"))
    if fmt.axis:
        out.extend(_grid(axis, cut, y, plot_left, plot_width) if fmt.gridlines else [])
        out.extend(_axis(axis, cut, y, plot_left, fmt))

    for c, category in enumerate(data.categories):
        slot_x = plot_left + c * slot
        column_x = slot_x + (slot - column_width) / 2
        if grouping == "stacked":
            out.extend(
                _stacked_column(data, c, column_x, column_width, y, cut, percent=percent, fmt=fmt)
            )
        else:
            out.extend(_clustered_column(data, c, column_x, column_width, y, cut, fmt))
        out.append(
            Text(
                slot_x, top_band + plot_height, slot, CATEGORY_BAND, category, "center", "category"
            )
        )

    def edges(category: int, series: int | None) -> tuple[float, float]:
        """Left and right edge of the measured column, or of one bar of a clustered column."""
        column_x = plot_left + category * slot + (slot - column_width) / 2
        if series is not None and grouping == "clustered":
            bar_width = column_width / len(data.series)
            return column_x + series * bar_width, column_x + (series + 1) * bar_width
        return column_x, column_x + column_width

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets a column: top centre, above its label."""
        left, right = edges(category, series)
        return (left + right) / 2, y(
            fold(column_top(data, grouping, category, series))
        ) - LABEL_HEIGHT - LANE_LINE_GAP

    def level(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge, at the measured value."""
        value = notes.measured_value(data, category, series) or 0.0
        return edges(category, series)[1], y(fold(value))

    for lane, arrow in enumerate(brackets):
        line_y = lanes_top + lanes - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, arrow.series),
                line_y,
                notes.label(arrow, data),
            )
        )
    for lane, arrow in enumerate(levels):
        arrow_x = plot_left + plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(
                level(arrow.start, arrow.series),
                level(arrow.end, arrow.series),
                arrow_x,
                notes.label(arrow, data),
            )
        )
    for lane, annotation in enumerate(lines):
        out.extend(
            _value_line(annotation, data, y, fold, plot_left, plot_width, len(levels), lane, fmt)
        )
    if fmt.series_names == "labels":
        out.extend(
            _series_names(
                data,
                grouping,
                y,
                fold,
                plot_left + plot_width + right_lanes * LEVEL_LANE_WIDTH,
            )
        )
    return tuple(out)


def _same(value: float) -> float:
    return value


def _axis(
    axis: Axis,
    cut: Break | None,
    y: _YScale,
    plot_left: float,
    fmt: Format,
) -> list[Primitive]:
    """The axis line and its tick labels (the grid is emitted separately, behind the columns)."""
    out: list[Primitive] = [
        Line(plot_left, y(axis.maximum), plot_left, y(axis.minimum), "axis"),
    ]
    for tick in visible_ticks(axis, cut):
        top = y(cut.fold(tick) if cut else tick) - TICK_HEIGHT / 2
        out.append(
            Text(
                0,
                top,
                plot_left - TICK_GAP,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "right",
                "axis",
            )
        )
    if cut:
        out.extend(_axis_break_mark(plot_left, y(cut.lower)))
    return out


def _grid(
    axis: Axis, cut: Break | None, y: _YScale, plot_left: float, plot_width: float
) -> list[Primitive]:
    """Light lines behind the columns, one per tick except zero (the baseline covers it)."""
    return [
        Line(
            plot_left,
            y(cut.fold(tick) if cut else tick),
            plot_left + plot_width,
            y(cut.fold(tick) if cut else tick),
            "grid",
        )
        for tick in visible_ticks(axis, cut)
        if tick != 0
    ]


def _axis_break_mark(x: float, y_break: float) -> list[Primitive]:
    """A white gap and two slanted lines across the vertical axis line."""
    top = y_break - BREAK_GAP / 2
    return [
        Rect(x - BREAK_GAP / 2, top, BREAK_GAP, BREAK_GAP, BACKGROUND),
        Line(x - BREAK_GAP / 2, top, x + BREAK_GAP / 2, top + BREAK_SLANT, "axis"),
        Line(
            x - BREAK_GAP / 2,
            top + BREAK_GAP - BREAK_SLANT,
            x + BREAK_GAP / 2,
            top + BREAK_GAP,
            "axis",
        ),
    ]


def _value_line(
    annotation: Annotation,
    data: ChartData,
    y: _YScale,
    fold: _YScale,
    plot_left: float,
    plot_width: float,
    lanes: int,
    lane: int,
    fmt: Format,
) -> list[Primitive]:
    level = value_line.resolved(annotation, data)
    if level is None:
        return []
    line_y = y(fold(level))
    label_x = plot_left + plot_width + (lanes + lane) * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
    return [
        Line(plot_left, line_y, plot_left + plot_width, line_y, "helper"),
        Text(
            label_x,
            line_y - LABEL_HEIGHT / 2,
            LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
            LABEL_HEIGHT,
            format_value(level, fmt),
            "left",
            "annotation",
        ),
    ]


def _series_names(
    data: ChartData,
    grouping: Grouping,
    y: _YScale,
    fold: _YScale,
    band_x: float,
) -> list[Primitive]:
    """One series name per series, level with the last column's segments or bars."""
    last = len(data.categories) - 1
    labelled: list[tuple[float, str]] = []
    if grouping == "stacked":
        positive = negative = 0.0
        for series in data.series:
            value = series.values[last]
            if value is None or value == 0:
                top = bottom = y(fold(positive + negative))
            elif value > 0:
                top, bottom = y(fold(positive + value)), y(fold(positive))
                positive += value
            else:
                top, bottom = y(negative), y(negative + value)
                negative += value
            labelled.append(((top + bottom) / 2 - LABEL_HEIGHT / 2, series.name))
    else:
        for series in data.series:
            value = series.values[last]
            top = y(fold(value)) if value is not None and value >= 0 else y(0)
            bottom = y(0) if value is not None and value >= 0 else y(fold(value or 0.0))
            labelled.append(((top + bottom) / 2 - LABEL_HEIGHT / 2, series.name))
    # Bottom-up, so ``spread`` can move a box up when the one below it would overlap.
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


def break_mark(x: float, width: float, y_break: float, overhang: float) -> list[Primitive]:
    """A white gap across a column or bar with two parallel slanted lines."""
    left, right, top = x - overhang, x + width + overhang, y_break - BREAK_GAP / 2
    return [
        Rect(left, top, right - left, BREAK_GAP, BACKGROUND),
        Line(left, top, right, top + BREAK_SLANT, "annotation"),
        Line(left, top + BREAK_GAP - BREAK_SLANT, right, top + BREAK_GAP, "annotation"),
    ]


def column_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format | None = None,
) -> tuple[int, int | None] | None:
    """The category (and, for a bar of a clustered chart, the series) at chart point (x, y).

    Uses the geometry of :func:`layout_column`. Points in the arrow lanes or outside the box hit
    nothing; between the bars of a clustered column, or on its labels below, the series is ``None``.
    """
    fmt = fmt or Format()
    brackets, levels = notes.arrows(annotations, data, "column")
    lines = notes.value_lines(annotations, data, "column")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    plot_left = AXIS_BAND if fmt.axis else 0.0
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - (len(levels) + len(lines)) * LEVEL_LANE_WIDTH - series_band
    if (
        not data.categories
        or not plot_left <= x < plot_left + plot_width
        or y < lanes_top + len(brackets) * LANE_HEIGHT
    ):
        return None
    slot = plot_width / len(data.categories)
    category = int((x - plot_left) // slot)
    if grouping == "stacked" or not data.series:
        return category, None
    column_width = slot * (1 - GAP_RATIO)
    offset = x - plot_left - category * slot - (slot - column_width) / 2
    if not 0 <= offset < column_width:
        return category, None
    return category, int(offset // (column_width / len(data.series)))


def bracket(
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


def level_arrow(
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
    data: ChartData,
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    *,
    percent: bool = False,
    fmt: Format,
) -> list[Primitive]:
    if percent:
        return _percent_column(data, c, x, width, y, fmt)
    out: list[Primitive] = []
    column_top_value = column_tops(data, "stacked")[c]
    fold = cut.fold if cut else _same
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
        label = format_value(value, fmt) if bottom - top >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(x, top, width, bottom - top, label, "center", "value", fill=i))
    if segments >= 2:  # a single segment's total would just repeat its own label
        out.append(
            Text(
                x,
                y(fold(positive)) - LABEL_HEIGHT,
                width,
                LABEL_HEIGHT,
                format_value(positive + negative, fmt),
                "center",
                "total",
            )
        )
    if cut and cut.cuts(column_top_value):
        out.extend(break_mark(x, width, y(cut.lower), BREAK_OVERHANG))
    return out


def _percent_column(
    data: ChartData, c: int, x: float, width: float, y: _YScale, fmt: Format
) -> list[Primitive]:
    """A 100 % high column: shares inside, the absolute column sum above it."""
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
        height = (value or 0.0) / total * 100
        top, bottom = y(level + height), y(level)
        level += height
        out.append(Rect(x, top, width, bottom - top, i))
        # Always emit the label (empty if flat): the structure must not depend on the size.
        label = percentage if bottom - top >= MIN_SEGMENT_FOR_LABEL else ""
        out.append(Text(x, top, width, bottom - top, label, "center", "value", fill=i))
    out.append(
        Text(
            x,
            y(100.0) - LABEL_HEIGHT,
            width,
            LABEL_HEIGHT,
            format_value(total, fmt),
            "center",
            "total",
        )
    )
    return out


def _clustered_column(
    data: ChartData,
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    fmt: Format,
) -> list[Primitive]:
    out: list[Primitive] = []
    fold = cut.fold if cut else _same
    bar_width = width / len(data.series)
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_x = x + i * bar_width
        top, bottom = (y(fold(value)), y(0)) if value >= 0 else (y(0), y(value))
        out.append(Rect(bar_x, top, bar_width, bottom - top, i))
        label_y = top - LABEL_HEIGHT if value >= 0 else bottom
        out.append(
            Text(
                bar_x,
                label_y,
                bar_width,
                LABEL_HEIGHT,
                format_value(value, fmt),
                "center",
                "value",
            )
        )
        if cut and cut.cuts(value):  # bars sit side by side: the mark stays on its bar
            out.extend(break_mark(bar_x, bar_width, y(cut.lower), 0.0))
    return out
