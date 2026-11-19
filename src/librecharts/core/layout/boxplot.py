"""Box plot layout: five-number summaries as boxes with whiskers (M24)."""

from __future__ import annotations

from librecharts.core.boxplot import BoxData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    axis_title,
    category_title,
    format_value,
    visible_ticks,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Marker, Primitive, Rect, Text
from librecharts.core.scale import nice_axis

TOP_BAND = 800.0
CATEGORY_BAND = 1000.0
BOX_WIDTH_RATIO = 0.5


def layout_boxplot(
    data: BoxData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """A box from Q1 to Q3, the median line, whiskers and outlier dots."""
    fmt = fmt or Format()
    if not data.rows:
        return ()
    numbers = [value for row in data.rows for value in (row.minimum, row.maximum, *row.outliers)]
    axis = nice_axis(min(numbers), max(numbers), include_zero=False)
    title_band = AXIS_BAND if fmt.axis_title else 0.0
    category_band = AXIS_BAND if fmt.category_axis_title else 0.0
    plot_left = title_band + (AXIS_BAND if fmt.axis else 0.0)
    plot_top = TOP_BAND
    plot_width = width - plot_left
    plot_height = height - plot_top - CATEGORY_BAND - category_band
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")

    def y(value: float) -> float:
        return plot_top + (axis.maximum - value) / (axis.maximum - axis.minimum) * plot_height

    slot = plot_width / len(data.rows)
    box_width = slot * BOX_WIDTH_RATIO
    out: list[Primitive] = []
    if fmt.axis:
        for tick in visible_ticks(axis):
            out.append(Line(plot_left, y(tick), plot_left + plot_width, y(tick), "grid"))
            out.append(
                Text(
                    0,
                    y(tick) - LABEL_HEIGHT / 2,
                    plot_left - 100,
                    LABEL_HEIGHT,
                    format_value(tick, fmt),
                    "right",
                    "axis",
                )
            )
    for index, row in enumerate(data.rows):
        centre = plot_left + (index + 0.5) * slot
        out.append(
            Rect(
                centre - box_width / 2,
                y(row.q3),
                box_width,
                y(row.q1) - y(row.q3),
                0,
                category=index,
            )
        )
        out.append(
            Line(
                centre - box_width / 2,
                y(row.median),
                centre + box_width / 2,
                y(row.median),
                "annotation",
            )
        )
        out.append(Line(centre, y(row.q3), centre, y(row.maximum), "annotation"))
        out.append(Line(centre, y(row.q1), centre, y(row.minimum), "annotation"))
        out.append(
            Line(
                centre - box_width / 4,
                y(row.maximum),
                centre + box_width / 4,
                y(row.maximum),
                "annotation",
            )
        )
        out.append(
            Line(
                centre - box_width / 4,
                y(row.minimum),
                centre + box_width / 4,
                y(row.minimum),
                "annotation",
            )
        )
        for value in row.outliers:
            out.append(Marker(centre, y(value), 0, category=index))
        out.append(
            Text(
                centre - slot / 2,
                plot_top + plot_height,
                slot,
                CATEGORY_BAND,
                row.label,
                "center",
                "category",
            )
        )
    if fmt.axis_title:
        out.extend(axis_title(fmt, 0, plot_top, title_band or AXIS_BAND, plot_height, rotated=True))
    if fmt.category_axis_title:
        out.extend(
            category_title(fmt, plot_left, plot_top + plot_height + CATEGORY_BAND, plot_width)
        )
    return tuple(out)
