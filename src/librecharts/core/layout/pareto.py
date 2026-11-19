"""Pareto charts: descending bars with a cumulative percentage line (M24)."""

from __future__ import annotations

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    format_share,
    format_value,
    legend_insets,
    visible_ticks,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Marker, Polyline, Primitive, Rect, Text
from librecharts.core.scale import nice_axis

TOP_BAND = 800.0
CATEGORY_BAND = 1000.0
RIGHT_AXIS = 1800.0
GAP_RATIO = 0.25


def layout_pareto(
    data: ChartData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Columns sorted descending and the cumulative share on a right-hand 0..100 % axis."""
    fmt = fmt or Format()
    if not data.categories or not data.series:
        return ()
    values = [value or 0.0 for value in data.series[0].values]
    order = sorted(range(len(values)), key=lambda index: -values[index])
    total = sum(values)
    if total <= 0:
        return ()
    inset_left, inset_top, inset_right, inset_bottom = legend_insets(fmt)
    plot_left = inset_left + (AXIS_BAND if fmt.axis else 0.0)
    plot_top = inset_top + TOP_BAND
    plot_width = width - plot_left - inset_right - RIGHT_AXIS
    plot_height = height - plot_top - inset_bottom - CATEGORY_BAND
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    axis = nice_axis(0.0, max(values))
    slot = plot_width / len(order)
    bar_width = slot * (1 - GAP_RATIO)

    def bar_height(value: float) -> float:
        return value / axis.maximum * plot_height

    out: list[Primitive] = []
    if fmt.axis:
        for tick in visible_ticks(axis):
            y = plot_top + plot_height - bar_height(tick)
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
    running = 0.0
    points: list[tuple[float, float]] = []
    for position, index in enumerate(order):
        value = values[index]
        running += value
        x = plot_left + position * slot + (slot - bar_width) / 2
        top = plot_top + plot_height - bar_height(value)
        out.append(Rect(x, top, bar_width, plot_top + plot_height - top, 0, category=index))
        out.append(
            Text(
                x,
                top - LABEL_HEIGHT - 50,
                bar_width,
                LABEL_HEIGHT,
                format_value(value, fmt),
                "center",
                "value",
            )
        )
        out.append(
            Text(
                x,
                plot_top + plot_height,
                slot,
                CATEGORY_BAND,
                data.categories[index],
                "center",
                "category",
            )
        )
        share = running / total * 100
        points.append((x + bar_width / 2, plot_top + plot_height - share / 100 * plot_height))
        out.append(
            Text(
                x + bar_width + 50,
                points[-1][1] - LABEL_HEIGHT / 2,
                1200,
                LABEL_HEIGHT,
                format_share(share, fmt),
                "left",
                "value",
            )
        )
    out.append(Polyline(tuple(points), 0))
    for x, y in points:
        out.append(Marker(x, y, 0))
    # The 80/20 helper line on the percentage axis.
    eighty = plot_top + plot_height - 0.8 * plot_height
    out.append(Line(plot_left, eighty, plot_left + plot_width, eighty, "helper"))
    for tick in (0, 25, 50, 75, 100):
        y = plot_top + plot_height - tick / 100 * plot_height
        out.append(
            Text(
                plot_left + plot_width + 100,
                y - LABEL_HEIGHT / 2,
                RIGHT_AXIS - 100,
                LABEL_HEIGHT,
                f"{tick} %",
                "left",
                "axis",
            )
        )
    return tuple(out)
