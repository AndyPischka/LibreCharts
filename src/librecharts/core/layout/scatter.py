"""Layout of scatter and bubble charts.

Both axes are always drawn: a scatter chart is unreadable without them. They do not have to
include zero. Points are markers, or bubbles when they have a size (the areas are proportional to
the sizes, the largest bubble is ``MAX_BUBBLE`` of the shorter plot side, but never reaches out of
the box). Points of one group share a colour; a legend names the groups. Value lines run in lanes
right of the plot; difference and CAGR arrows (M14) measure the points' y values, in bracket lanes
above the plot or level lanes right of it. A CAGR counts the x distance of its two points.

The kinds and order of the primitives depend on the data only, never on the size (ADR 0007).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.layout.column import LANE_HEIGHT, LANE_LINE_GAP
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    TICK_GAP,
    TICK_HEIGHT,
    bracket,
    format_value,
    legend,
    level_arrow,
)
from librecharts.core.model import Annotation, Format, LabelKey
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
PICK_TOLERANCE = 900.0  # how far a click may miss a point and still pick it, 1/100 mm

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
    brackets, level_arrows = notes.arrows(annotations, measured, "scatter")
    top = TOP_BAND + (LEGEND_HEIGHT if any(data.groups) else 0.0) + len(brackets) * LANE_HEIGHT
    plot_left = AXIS_BAND
    plot_width = (
        width - plot_left - RIGHT_BAND - (len(lines) + len(level_arrows)) * LEVEL_LANE_WIDTH
    )
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

    diameters = _bubble_diameters(data, top, plot_width, plot_height)
    # Big bubbles first, so that small ones stay visible on top of them.
    sized = sorted(
        ((p, d) for p, d in zip(data.points, diameters, strict=True) if d > 0.0),
        key=lambda item: -(item[0].size or 0.0),
    )
    out.extend(Bubble(x(p.x), y(p.y), d, p.group) for p, d in sized)
    out.extend(
        Marker(x(p.x), y(p.y), p.group)
        for p, d in zip(data.points, diameters, strict=True)
        if d == 0.0
    )
    for number, point in enumerate(data.points):
        if not point.label:
            continue
        reach = (MARKER_SIZE if diameters[number] == 0.0 else diameters[number]) / 2
        left = x(point.x) + reach + LABEL_GAP
        out.append(
            Text(
                left,
                y(point.y) - LABEL_HEIGHT / 2,
                min(LABEL_WIDTH, width - left),  # ends at the box, like the bubbles
                LABEL_HEIGHT,
                point.label,
                "left",
                "value",
                key=LabelKey("value", number),
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

    def anchor(index: int) -> tuple[float, float]:
        """Where an arrow meets the point: above the marker or the top of the bubble."""
        point = data.points[index]
        reach = (MARKER_SIZE if diameters[index] == 0.0 else diameters[index]) / 2
        return x(point.x), y(point.y) - reach

    for lane, arrow in enumerate(brackets):
        line_y = top - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(
                anchor(arrow.start),
                anchor(arrow.end),
                line_y,
                notes.label(arrow, measured, tuple(point.x for point in data.points)),
            )
        )
    for lane, arrow in enumerate(level_arrows):
        arrow_x = (
            plot_left
            + plot_width
            + RIGHT_BAND
            + (len(shown) + lane) * LEVEL_LANE_WIDTH
            + LEVEL_ARROW_INSET
        )
        out.extend(
            level_arrow(
                anchor(arrow.start),
                anchor(arrow.end),
                arrow_x,
                notes.label(arrow, measured, tuple(point.x for point in data.points)),
            )
        )
    return tuple(out)


def _bubble_diameters(
    data: ScatterData, top: float, plot_width: float, plot_height: float
) -> list[float]:
    """The diameter of every point's bubble, 0 for a plain marker (shared with the hit test)."""
    biggest = max((p.size for p in data.points if p.size is not None), default=0.0)
    if biggest <= 0:
        return [0.0] * len(data.points)
    # A bubble on the edge of the plot must not reach out of the box: the group shape would grow,
    # and every redraw at the group's size would widen the chart further.
    edge = min(top, AXIS_BAND, X_AXIS_BAND, RIGHT_BAND)
    largest = min(MAX_BUBBLE * min(plot_width, plot_height), 2 * edge)
    return [largest * math.sqrt((p.size or 0.0) / biggest) for p in data.points]


def scatter_at(
    data: ScatterData,
    width: float,
    height: float,
    x: float,
    y: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[int, None] | None:
    """The point at chart point (x, y), or ``None``.

    Uses the geometry of :func:`layout_scatter`; a click near a point picks it, inside a bubble
    everywhere, but points in the annotation lanes or outside the plot hit nothing.
    """
    fmt = fmt or Format()
    measured = levels(data)
    lines = notes.value_lines(annotations, measured, "scatter")
    brackets, level_arrows = notes.arrows(annotations, measured, "scatter")
    top = TOP_BAND + (LEGEND_HEIGHT if any(data.groups) else 0.0) + len(brackets) * LANE_HEIGHT
    plot_left = AXIS_BAND
    plot_width = (
        width - plot_left - RIGHT_BAND - (len(lines) + len(level_arrows)) * LEVEL_LANE_WIDTH
    )
    plot_height = height - top - X_AXIS_BAND
    if not data.points or plot_width <= 0 or plot_height <= 0:
        return None
    if not plot_left <= x <= plot_left + plot_width or not top <= y <= top + plot_height:
        return None
    shown = [level for level in (value_line.resolved(a, measured) for a in lines) if level]
    xs = [point.x for point in data.points]
    ys = [point.y for point in data.points] + shown
    x_axis = nice_axis(min(xs), max(xs), include_zero=False)
    y_axis = nice_axis(min(ys), max(ys), include_zero=False)

    def px(value: float) -> float:
        return plot_left + (value - x_axis.minimum) / (x_axis.maximum - x_axis.minimum) * plot_width

    def py(value: float) -> float:
        return top + (y_axis.maximum - value) / (y_axis.maximum - y_axis.minimum) * plot_height

    diameters = _bubble_diameters(data, top, plot_width, plot_height)
    best: tuple[float, int] | None = None
    for index, point in enumerate(data.points):
        distance = math.hypot(x - px(point.x), y - py(point.y))
        reach = (diameters[index] if diameters[index] > 0.0 else MARKER_SIZE) / 2
        if distance - reach > PICK_TOLERANCE:
            continue
        if best is None or distance - reach < best[0]:
            best = (distance - reach, index)
    if best is None:
        return None
    return best[1], None


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
