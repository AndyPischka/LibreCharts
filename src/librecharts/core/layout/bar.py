"""Layout of stacked and clustered bar charts (horizontal columns).

Categories run top to bottom in data order, values left to right. As in the column layout no value
axis is drawn and the kinds and order of the primitives depend only on the data, never on the size.
Category names sit in a band on the left, outside labels (totals, clustered values) on the right
of the bars. Negative values grow to the left and their outside labels get extra room next to the
names.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import GAP_RATIO, format_value, value_axis
from librecharts.core.model import Grouping
from librecharts.core.primitives import Line, Primitive, Rect, Text

LEFT_BAND = 3000.0  # room left of the plot for category names
RIGHT_BAND = 1200.0  # room right of the plot for outside labels of positive values and totals
LABEL_WIDTH = 1200.0  # width of an outside value or total label box (incl. LABEL_GAP)
LABEL_HEIGHT = 600.0
LABEL_GAP = 150.0  # between a bar end and its outside label, and before the category names
MIN_SEGMENT_FOR_LABEL = 800.0  # segments narrower than this get no inside label

_XScale = Callable[[float], float]


def layout_bar(
    data: ChartData, grouping: Grouping, width: float, height: float
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    # Labels of negative bars hang to the left of them and must not run into the category names.
    plot_left = LEFT_BAND + (LABEL_WIDTH if has_negative else 0.0)
    plot_width = width - plot_left - RIGHT_BAND
    if height <= 0 or plot_width <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    axis = value_axis(data, grouping)
    span = axis.maximum - axis.minimum

    def x(value: float) -> float:
        return plot_left + (value - axis.minimum) / span * plot_width

    slot = height / len(data.categories)
    thickness = slot * (1 - GAP_RATIO)
    out: list[Primitive] = [Line(x(0), 0, x(0), height, "baseline")]

    for c, category in enumerate(data.categories):
        slot_y = c * slot
        bar_y = slot_y + (slot - thickness) / 2
        if grouping == "stacked":
            out.extend(_stacked_bar(data, c, bar_y, thickness, x))
        else:
            out.extend(_clustered_bar(data, c, bar_y, thickness, x))
        out.append(
            Text(0, slot_y, LEFT_BAND - LABEL_GAP, slot, category, "right", "category"),
        )
    return tuple(out)


def _stacked_bar(
    data: ChartData, c: int, y: float, thickness: float, x: _XScale
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
    return out


def _clustered_bar(
    data: ChartData, c: int, y: float, thickness: float, x: _XScale
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
    return out
