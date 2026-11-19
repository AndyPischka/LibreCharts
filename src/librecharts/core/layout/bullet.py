"""Bullet charts: one KPI bar per row with a target marker (M24)."""

from __future__ import annotations

from librecharts.core.bullet import BulletData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    axis_title,
    category_title,
    format_value,
    visible_ticks,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Primitive, Rect, Text
from librecharts.core.scale import nice_axis

TOP_BAND = 800.0
CATEGORY_BAND = 1000.0
LABEL_WIDTH = 1800.0
BAR_HEIGHT = 1400.0


def layout_bullet(
    data: BulletData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Solid actual bars, a target tick and an optional qualitative band."""
    fmt = fmt or Format()
    if not data.rows:
        return ()
    maximum = max(row.maximum for row in data.rows)
    axis = nice_axis(0.0, maximum)
    title_band = AXIS_BAND if fmt.axis_title else 0.0
    category_band = AXIS_BAND if fmt.category_axis_title else 0.0
    plot_left = title_band + (AXIS_BAND if fmt.axis else 0.0)
    plot_top = TOP_BAND
    plot_width = width - plot_left
    plot_height = height - plot_top - CATEGORY_BAND - category_band
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")

    def x(value: float) -> float:
        return plot_left + value / axis.maximum * plot_width

    slot = plot_height / len(data.rows)
    out: list[Primitive] = []
    if fmt.axis:
        for tick in visible_ticks(axis):
            out.append(Line(x(tick), plot_top, x(tick), plot_top + plot_height, "grid"))
            out.append(
                Text(
                    x(tick) - 300,
                    plot_top + plot_height,
                    600,
                    LABEL_HEIGHT,
                    format_value(tick, fmt),
                    "center",
                    "axis",
                )
            )
    for index, row in enumerate(data.rows):
        centre = plot_top + (index + 0.5) * slot
        thickness = min(BAR_HEIGHT, slot * 0.5)
        out.append(
            Text(
                0,
                centre - LABEL_HEIGHT / 2,
                plot_left - 100,
                LABEL_HEIGHT,
                row.label,
                "right",
                "category",
            )
        )
        if row.qualitative is not None and row.qualitative > 0:
            out.append(
                Rect(
                    plot_left,
                    centre - thickness / 2,
                    x(min(row.qualitative, maximum)) - plot_left,
                    thickness,
                    1,
                    category=index,
                )
            )
        out.append(
            Rect(
                plot_left,
                centre - thickness / 2,
                x(min(row.actual, maximum)) - plot_left,
                thickness,
                0,
                category=index,
            )
        )
        if row.target is not None:
            target = x(min(max(row.target, 0.0), maximum))
            out.append(Line(target, centre - thickness, target, centre + thickness, "annotation"))
        out.append(
            Text(
                min(x(min(row.actual, maximum)) + 100, width - LABEL_WIDTH),
                centre - LABEL_HEIGHT / 2,
                LABEL_WIDTH,
                LABEL_HEIGHT,
                format_value(row.actual, fmt),
                "left",
                "value",
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
    return tuple(out)
