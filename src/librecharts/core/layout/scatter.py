"""Layout of scatter and bubble charts.

Both axes are always drawn: a scatter chart is unreadable without them. They do not have to
include zero. Points are markers, or bubbles when they have a size (the areas are proportional to
the sizes, the largest bubble is ``MAX_BUBBLE`` of the shorter plot side). Points of one group share
a colour; a legend names the groups. The only annotation is a horizontal value line.

The kinds and order of the primitives depend on the data only, never on the size (ADR 0007).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    TICK_GAP,
    TICK_HEIGHT,
    format_value,
    legend,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import MARKER_SIZE, Bubble, Line, Marker, Primitive, Text
from librecharts.core.scale import Axis, nice_axis
from librecharts.core.scatter import ScatterData, levels

TOP_BAND = 600.0  # room above the plot so that the topmost marker or bubble is not cut off
X_AXIS_BAND = 1000.0  # room below the plot for the x tick labels
RIGHT_BAND = 1800.0  # room right of the plot for the label of the rightmost point
LABEL_WIDTH = 2400.0  # width of a point label box
LABEL_GAP = 100.0  # between a marker and its label
TICK_WIDTH = 1600.0  # width of an x tick label box
MAX_BUBBLE = 0.12  # diameter of the largest bubble, as a share of the shorter plot side

_Scale = Callable[[float], float]


def layout_scatter(
    data: ScatterData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    measured = levels(data)
    lines = notes.value_lines(annotations, measured, "scatter")
    top = TOP_BAND + (LEGEND_HEIGHT if any(data.groups) else 0.0)
    plot_left = AXIS_BAND
    plot_width = width - plot_left - RIGHT_BAND - len(lines) * LEVEL_LANE_WIDTH
    plot_height = height - top - X_AXIS_BAND
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not data.points:
        return ()

    marked = [value_line.resolved(annotation, measured) for annotation in lines]
    shown = [level for level in marked if level is not None]
    xs = [point.x for point in data.points]
    ys = [point.y for point in data.points] + shown
    x_axis = nice_axis(min(xs), max(xs), include_zero=False)
    y_axis = nice_axis(min(ys), max(ys), include_zero=False)

    def x(value: float) -> float:
        return plot_left + (value - x_axis.minimum) / (x_axis.maximum - x_axis.minimum) * plot_width

    def y(value: float) -> float:
        return top + (y_axis.maximum - value) / (y_axis.maximum - y_axis.minimum) * plot_height

    plot_bottom = top + plot_height
    out: list[Primitive] = []
    if any(data.groups):
        out.extend(legend(list(data.groups), width))
    if fmt.gridlines:
        out.extend(_grid(x_axis, y_axis, x, y, plot_left, plot_width, top, plot_bottom))
    out.extend(_axes(x_axis, y_axis, x, y, plot_left, plot_bottom, fmt))

    biggest = max((p.size for p in data.points if p.size is not None), default=0.0)
    largest = MAX_BUBBLE * min(plot_width, plot_height)

    def diameter(size: float) -> float:
        return largest * math.sqrt(size / biggest)  # area proportional to the size

    # Big bubbles first, so that small ones stay visible on top of them.
    sized = sorted((p for p in data.points if p.size is not None), key=lambda p: -(p.size or 0.0))
    out.extend(Bubble(x(p.x), y(p.y), diameter(p.size or 0.0), p.group) for p in sized)
    out.extend(Marker(x(p.x), y(p.y), p.group) for p in data.points if p.size is None)
    for point in data.points:
        if not point.label:
            continue
        reach = (MARKER_SIZE if point.size is None else diameter(point.size)) / 2
        out.append(
            Text(
                x(point.x) + reach + LABEL_GAP,
                y(point.y) - LABEL_HEIGHT / 2,
                LABEL_WIDTH,
                LABEL_HEIGHT,
                point.label,
                "left",
                "value",
            )
        )
    for lane, level in enumerate(marked):
        if level is None:
            continue
        label_x = plot_left + plot_width + RIGHT_BAND + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            (
                Line(plot_left, y(level), plot_left + plot_width, y(level), "helper"),
                Text(
                    label_x,
                    y(level) - LABEL_HEIGHT / 2,
                    LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
                    LABEL_HEIGHT,
                    format_value(level, fmt),
                    "left",
                    "annotation",
                ),
            )
        )
    return tuple(out)


def _grid(
    x_axis: Axis,
    y_axis: Axis,
    x: _Scale,
    y: _Scale,
    plot_left: float,
    plot_width: float,
    plot_top: float,
    plot_bottom: float,
) -> list[Primitive]:
    """Light lines at every tick except the first one (the axis covers it)."""
    return [
        *(
            Line(plot_left, y(tick), plot_left + plot_width, y(tick), "grid")
            for tick in y_axis.ticks()
            if tick != y_axis.minimum
        ),
        *(
            Line(x(tick), plot_top, x(tick), plot_bottom, "grid")
            for tick in x_axis.ticks()
            if tick != x_axis.minimum
        ),
    ]


def _axes(
    x_axis: Axis,
    y_axis: Axis,
    x: _Scale,
    y: _Scale,
    plot_left: float,
    plot_bottom: float,
    fmt: Format,
) -> list[Primitive]:
    out: list[Primitive] = [
        Line(plot_left, y(y_axis.maximum), plot_left, plot_bottom, "axis"),
        Line(plot_left, plot_bottom, x(x_axis.maximum), plot_bottom, "axis"),
    ]
    out.extend(
        Text(
            0,
            y(tick) - TICK_HEIGHT / 2,
            plot_left - TICK_GAP,
            TICK_HEIGHT,
            format_value(tick, fmt),
            "right",
            "axis",
        )
        for tick in y_axis.ticks()
    )
    out.extend(
        Text(
            x(tick) - TICK_WIDTH / 2,
            plot_bottom + TICK_GAP,
            TICK_WIDTH,
            TICK_HEIGHT,
            format_value(tick, fmt),
            "center",
            "axis",
        )
        for tick in x_axis.ticks()
    )
    return out
