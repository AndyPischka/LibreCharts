"""Dumbbell (slope) charts: two points per category with a connector (M24)."""

from __future__ import annotations

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    axis_title,
    category_title,
    format_value,
    legend_insets,
    visible_ticks,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Marker, Primitive, Text
from librecharts.core.scale import nice_axis

TOP_BAND = 800.0
CATEGORY_BAND = 1000.0
LABEL_GAP = 50.0  # between a marker and its value label
LABEL_BAND = LABEL_HEIGHT + LABEL_GAP  # room below a vertical plot for the lower labels
LABEL_WIDTH = 1800.0


def layout_dumbbell(
    data: ChartData,
    width: float,
    height: float,
    fmt: Format | None = None,
    *,
    horizontal: bool = True,
    length_per_unit: float | None = None,
) -> tuple[Primitive, ...]:
    """Two markers and a connector per category, horizontal by default."""
    fmt = fmt or Format()
    if not data.categories or len(data.series) < 2:
        return ()
    starts, ends = data.series[0], data.series[1]
    values = [
        value
        for pair in zip(starts.values, ends.values, strict=True)
        for value in pair
        if value is not None
    ]
    if not values:
        return ()
    axis = nice_axis(min(values), max(values), include_zero=False)
    inset_left, inset_top, inset_right, inset_bottom = legend_insets(fmt)
    show_axis = fmt.axis
    title_band = AXIS_BAND if fmt.axis_title else 0.0
    plot_left = inset_left + title_band + (AXIS_BAND if show_axis else 0.0)
    plot_top = inset_top + TOP_BAND
    label_band = 0.0 if horizontal else LABEL_BAND
    plot_width = width - plot_left - inset_right
    plot_height = height - plot_top - inset_bottom - CATEGORY_BAND - label_band
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")

    def fraction(value: float) -> float:
        return (value - axis.minimum) / (axis.maximum - axis.minimum)

    out: list[Primitive] = []
    if horizontal:
        slot = plot_height / len(data.categories)
        for index, category in enumerate(data.categories):
            start, end = starts.values[index], ends.values[index]
            centre = plot_top + (index + 0.5) * slot
            out.append(
                Text(
                    0,
                    centre - LABEL_HEIGHT / 2,
                    plot_left - 100,
                    LABEL_HEIGHT,
                    category,
                    "right",
                    "category",
                )
            )
            plotted = [
                (value, plot_left + fraction(value) * plot_width)
                for value in (start, end)
                if value is not None
            ]
            if len(plotted) == 2:
                out.append(Line(plotted[0][1], centre, plotted[1][1], centre, "connector"))
            for value, x in plotted:
                out.append(Marker(x, centre, 0))
                out.append(
                    Text(
                        min(max(x - LABEL_WIDTH / 2, 0.0), width - LABEL_WIDTH),
                        max(centre - LABEL_HEIGHT - LABEL_GAP, 0.0),
                        LABEL_WIDTH,
                        LABEL_HEIGHT,
                        format_value(value, fmt),
                        "center",
                        "value",
                    )
                )
        if show_axis:
            for tick in visible_ticks(axis):
                x = plot_left + fraction(tick) * plot_width
                out.append(Line(x, plot_top, x, plot_top + plot_height, "grid"))
                out.append(
                    Text(
                        x - 300,
                        plot_top + plot_height,
                        600,
                        LABEL_HEIGHT,
                        format_value(tick, fmt),
                        "center",
                        "axis",
                    )
                )
            out.append(
                Line(
                    plot_left,
                    plot_top + plot_height,
                    plot_left + plot_width,
                    plot_top + plot_height,
                    "axis",
                )
            )
        if fmt.axis_title:
            out.extend(
                axis_title(fmt, 0, plot_top, title_band or AXIS_BAND, plot_height, rotated=False)
            )
        if fmt.category_axis_title:
            out.extend(
                category_title(fmt, plot_left, plot_top + plot_height + CATEGORY_BAND, plot_width)
            )
    else:
        slot = plot_width / len(data.categories)
        for index, category in enumerate(data.categories):
            start, end = starts.values[index], ends.values[index]
            centre = plot_left + (index + 0.5) * slot
            out.append(
                Text(
                    centre - slot / 2,
                    plot_top + plot_height + label_band,
                    slot,
                    CATEGORY_BAND,
                    category,
                    "center",
                    "category",
                )
            )
            plotted = [
                (value, plot_top + (1 - fraction(value)) * plot_height)
                for value in (start, end)
                if value is not None
            ]
            if len(plotted) == 2:
                out.append(Line(centre, plotted[0][1], centre, plotted[1][1], "connector"))
            lowest = max((y for _, y in plotted), default=0.0)
            for value, y in plotted:
                out.append(Marker(centre, y, 0))
                below = len(plotted) == 2 and y == lowest
                out.append(
                    Text(
                        centre - slot / 2,
                        y + LABEL_GAP if below else max(y - LABEL_HEIGHT - LABEL_GAP, 0.0),
                        slot,
                        LABEL_HEIGHT,
                        format_value(value, fmt),
                        "center",
                        "value",
                    )
                )
        if show_axis:
            for tick in visible_ticks(axis):
                y = plot_top + (1 - fraction(tick)) * plot_height
                out.append(Line(plot_left, y, plot_left + plot_width, y, "grid"))
                out.append(
                    Text(
                        0,
                        y - LABEL_HEIGHT / 2,
                        plot_left - 100,
                        LABEL_HEIGHT,
                        format_value(tick, fmt),
                        "right",
                        "axis",
                    )
                )
    return tuple(out)
