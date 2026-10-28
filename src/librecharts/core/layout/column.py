"""Layout of stacked and clustered column charts.

The kinds and order of the returned primitives depend only on the data, never on the size.

No value axis is drawn (like think-cell): values are labelled directly. The axis range only
fixes the scale and always includes zero. Above the plot there is a band for total and value
labels, below it a band for category labels. Bracket arrows (difference, CAGR) run in lanes
above the label band, one lane per arrow, the first one closest to the plot. Level arrows run in
lanes right of the plot, the first one closest to it.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import GAP_RATIO, format_value, value_axis
from librecharts.core.model import Annotation, Grouping
from librecharts.core.primitives import Line, Primitive, Rect, Text

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

    axis = value_axis(data, grouping)
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
            out.extend(_stacked_column(data, c, column_x, column_width, y))
        else:
            out.extend(_clustered_column(data, c, column_x, column_width, y))
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

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets a column: top centre, above its label."""
        values = [v for s in data.series if (v := s.values[category]) is not None]
        if series is not None and grouping == "clustered":
            top = max(data.series[series].values[category] or 0.0, 0.0)
        elif grouping == "clustered":
            top = max([0.0, *values])
        else:
            top = sum(v for v in values if v > 0)
        left, right = edges(category, series)
        return (left + right) / 2, y(top) - LABEL_HEIGHT - LANE_LINE_GAP

    def level(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge, at the measured value."""
        return edges(category, series)[1], y(notes.measured_value(data, category, series) or 0.0)

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


def _arrows(
    data: ChartData, annotations: tuple[Annotation, ...]
) -> tuple[list[Annotation], list[Annotation]]:
    """The drawable arrows: (bracket arrows above the plot, level arrows right of it)."""
    shown = [a for a in annotations if notes.drawable(a, data, "column")]
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


def _stacked_column(data: ChartData, c: int, x: float, width: float, y: _YScale) -> list[Primitive]:
    out: list[Primitive] = []
    positive = negative = 0.0
    segments = 0
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None or value == 0:
            continue
        segments += 1
        if value > 0:
            top, bottom = y(positive + value), y(positive)
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
                y(positive) - LABEL_HEIGHT,
                width,
                LABEL_HEIGHT,
                format_value(positive + negative),
                "center",
                "total",
            )
        )
    return out


def _clustered_column(
    data: ChartData, c: int, x: float, width: float, y: _YScale
) -> list[Primitive]:
    out: list[Primitive] = []
    bar_width = width / len(data.series)
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_x = x + i * bar_width
        top, bottom = (y(value), y(0)) if value >= 0 else (y(0), y(value))
        out.append(Rect(bar_x, top, bar_width, bottom - top, i))
        label_y = top - LABEL_HEIGHT if value >= 0 else bottom
        out.append(
            Text(bar_x, label_y, bar_width, LABEL_HEIGHT, format_value(value), "center", "value")
        )
    return out
