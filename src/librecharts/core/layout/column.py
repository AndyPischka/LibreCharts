"""Layout of stacked and clustered column charts.

No value axis is drawn (like think-cell): values are labelled directly. The axis range only
fixes the scale and always includes zero. Above the plot there is a band for total and value
labels, below it a band for category labels.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core.datasheet import ChartData
from librecharts.core.model import Grouping
from librecharts.core.primitives import Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, nice_axis

TOP_BAND = 800.0  # room above the plot for total / outside value labels
LABEL_HEIGHT = 600.0  # height of a value or total label box
CATEGORY_BAND = 1000.0  # room below the plot for category names
GAP_RATIO = 0.3  # share of a category slot left empty between columns
MIN_SEGMENT_FOR_LABEL = 500.0  # segments flatter than this get no inside label

_YScale = Callable[[float], float]


def layout_column(
    data: ChartData, grouping: Grouping, width: float, height: float
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    plot_height = height - TOP_BAND - CATEGORY_BAND
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    # Labels of negative columns hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    axis = _axis(data, grouping)
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        return TOP_BAND + (axis.maximum - value) / span * scale_height

    slot = width / len(data.categories)
    column_width = slot * (1 - GAP_RATIO)
    out: list[Primitive] = [Line(0, y(0), width, y(0), "baseline")]

    for c, category in enumerate(data.categories):
        slot_x = c * slot
        column_x = slot_x + (slot - column_width) / 2
        if grouping == "stacked":
            out.extend(_stacked_column(data, c, column_x, column_width, y))
        else:
            out.extend(_clustered_column(data, c, column_x, column_width, y))
        out.append(
            Text(
                slot_x, TOP_BAND + plot_height, slot, CATEGORY_BAND, category, "center", "category"
            )
        )
    return tuple(out)


def format_value(value: float) -> str:
    """Locale-neutral label text: integers plain, others with at most two decimals."""
    if value == round(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def _axis(data: ChartData, grouping: Grouping) -> Axis:
    if grouping == "stacked":
        lows: list[float] = []
        highs: list[float] = []
        for c in range(len(data.categories)):
            column = [v for s in data.series if (v := s.values[c]) is not None]
            lows.append(sum(v for v in column if v < 0))
            highs.append(sum(v for v in column if v > 0))
        return nice_axis(min(lows), max(highs))
    values = [v for s in data.series for v in s.values if v is not None]
    return nice_axis(min(values, default=0.0), max(values, default=0.0))


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
        if bottom - top >= MIN_SEGMENT_FOR_LABEL:
            out.append(Text(x, top, width, bottom - top, format_value(value), "center", "value"))
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
