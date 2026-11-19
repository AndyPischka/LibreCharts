"""2x2 matrix layout: quadrant lines, points and titles (M25)."""

from __future__ import annotations

from librecharts.core.layout.common import AXIS_BAND, LABEL_HEIGHT
from librecharts.core.matrix import MatrixData
from librecharts.core.model import Format, MatrixSpec
from librecharts.core.primitives import Bubble, Line, Marker, Primitive, Text
from librecharts.core.scale import nice_axis

TOP_BAND = 800.0
BOTTOM_BAND = 1600.0
LABEL_WIDTH = 2200.0


def layout_matrix(
    data: MatrixData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """A plot box with two quadrant lines, a marker or bubble per point and its label."""
    fmt = fmt or Format()
    spec = data.spec
    if not data.points:
        return ()
    xs = [point.x for point in data.points]
    ys = [point.y for point in data.points]
    x_axis = nice_axis(min(xs), max(xs), include_zero=False)
    y_axis = nice_axis(min(ys), max(ys), include_zero=False)
    x_split = spec.x_split if spec.x_split is not None else (x_axis.minimum + x_axis.maximum) / 2
    y_split = spec.y_split if spec.y_split is not None else (y_axis.minimum + y_axis.maximum) / 2
    plot_left, plot_top = AXIS_BAND, TOP_BAND
    plot_width = width - plot_left - 200
    plot_height = height - plot_top - BOTTOM_BAND
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")

    def x(value: float) -> float:
        return plot_left + (value - x_axis.minimum) / (x_axis.maximum - x_axis.minimum) * plot_width

    def y(value: float) -> float:
        return plot_top + (y_axis.maximum - value) / (y_axis.maximum - y_axis.minimum) * plot_height

    out: list[Primitive] = [
        Line(plot_left, plot_top, plot_left, plot_top + plot_height, "axis"),
        Line(
            plot_left,
            plot_top + plot_height,
            plot_left + plot_width,
            plot_top + plot_height,
            "axis",
        ),
        Line(x(x_split), plot_top, x(x_split), plot_top + plot_height, "grid"),
        Line(plot_left, y(y_split), plot_left + plot_width, y(y_split), "grid"),
    ]
    _quadrants(out, spec, x(x_split), y(y_split), plot_left, plot_top, plot_width, plot_height)
    _titles(out, spec, plot_left, plot_top, plot_width, plot_height)
    sizes = _sizes(data)
    for point, diameter in zip(data.points, sizes, strict=True):
        if diameter > 0:
            out.append(
                Bubble(
                    x(point.x), y(point.y), diameter, point.group, category=data.points.index(point)
                )
            )
        else:
            out.append(
                Marker(x(point.x), y(point.y), point.group, category=data.points.index(point))
            )
        if spec.labels:
            out.append(
                Text(
                    min(max(x(point.x) + 120, 0.0), width - LABEL_WIDTH),
                    max(y(point.y) - LABEL_HEIGHT - 50, 0.0),
                    LABEL_WIDTH,
                    LABEL_HEIGHT,
                    point.label,
                    "left",
                    "annotation",
                )
            )
    return tuple(out)


def _sizes(data: MatrixData) -> list[float]:
    if not data.spec.bubbles:
        return [0.0] * len(data.points)
    values = [point.size or 0.0 for point in data.points]
    largest = max(values, default=0.0)
    if largest <= 0:
        return [0.0] * len(data.points)
    return [300.0 + 900.0 * (value / largest) ** 0.5 for value in values]


def _quadrants(
    out: list[Primitive],
    spec: MatrixSpec,
    split_x: float,
    split_y: float,
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    positions = (
        (left, top, split_x - left, split_y - top),
        (split_x, top, left + width - split_x, split_y - top),
        (left, split_y, split_x - left, top + height - split_y),
        (split_x, split_y, left + width - split_x, top + height - split_y),
    )
    for label, (x, y, w, h) in zip(spec.quadrants, positions, strict=True):
        if label:
            out.append(Text(x, y, w, min(h, 600.0), label, "center", "heading"))


def _titles(
    out: list[Primitive],
    spec: MatrixSpec,
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    if spec.x_title:
        out.append(Text(left, top + height + 600, width, 500, spec.x_title, "center", "axis"))
    if spec.y_title:
        out.append(Text(0, top, left - 100, height, spec.y_title, "center", "axis", rotation=90))
    if spec.x_low:
        out.append(Text(left, top + height + 100, 1200, 400, spec.x_low, "left", "axis"))
    if spec.x_high:
        out.append(
            Text(left + width - 1200, top + height + 100, 1200, 400, spec.x_high, "right", "axis")
        )
    if spec.y_low:
        out.append(Text(left - 1100, top + height - 400, 1000, 400, spec.y_low, "right", "axis"))
    if spec.y_high:
        out.append(Text(left - 1100, top, 1000, 400, spec.y_high, "right", "axis"))
