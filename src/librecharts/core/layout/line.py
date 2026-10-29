"""Layout of line charts.

One line per series through the category slots, with point markers, a value label at every point
and the series name right of its last point. An empty value splits a series into several lines, so
the primitive structure depends on the data and the format only, never on the size.

As in the column layout, a value axis is optional; arrows (difference, CAGR) run in lanes above the
plot, level arrows and value lines in lanes right of it. An axis break shortens the value scale.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.axis_break import Break, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LABEL_HEIGHT,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    bracket,
    format_value,
    legend,
    level_arrow,
    point_runs,
    spread,
    value_axis,
    vertical_axis,
    vertical_grid,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import Line, Marker, Polyline, Primitive, Text
from librecharts.core.scale import Axis

TOP_BAND = 800.0  # room above the plot for the highest value labels
LABEL_GAP = 100.0  # between a marker and its value label
CATEGORY_BAND = 1000.0  # room below the plot for category names
LANE_HEIGHT = 800.0  # room for one arrow above the plot: its label and line
LANE_LINE_GAP = 100.0  # between an arrow's line and the point below it
SERIES_BAND = 2600.0  # room right of the lanes for series names
SERIES_LABEL_GAP = 150.0  # between the lanes and a series name
PICK_TOLERANCE = 900.0  # how far a click may miss a point and still pick it, 1/100 mm

_YScale = Callable[[float], float]


@dataclass(frozen=True, slots=True)
class _Plot:
    plot_left: float
    top_band: float
    plot_width: float
    plot_height: float
    axis: Axis
    cut: Break | None
    brackets: list[Annotation]
    levels: list[Annotation]
    value_lines: list[Annotation]


def layout_line(
    data: ChartData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    plot = _plot(data, width, height, annotations, fmt)
    if not data.categories or not data.series:
        return ()

    axis, cut = plot.axis, plot.cut
    span = axis.maximum - axis.minimum
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    scale_height = plot.plot_height - (LABEL_HEIGHT if has_negative else 0.0)

    def y(value: float) -> float:
        return plot.top_band + (axis.maximum - value) / span * scale_height

    fold = cut.fold if cut else _same
    slot = plot.plot_width / len(data.categories)
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    out.append(Line(plot.plot_left, y(0), plot.plot_left + plot.plot_width, y(0), "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(vertical_grid(axis, cut, y, plot.plot_left, plot.plot_width))
        out.extend(vertical_axis(axis, cut, y, plot.plot_left, fmt))

    for c, category in enumerate(data.categories):
        out.append(
            Text(
                plot.plot_left + c * slot,
                plot.top_band + plot.plot_height,
                slot,
                CATEGORY_BAND,
                category,
                "center",
                "category",
            )
        )

    for index, series in enumerate(data.series):
        points = [
            (plot.plot_left + (c + 0.5) * slot, y(fold(v)))
            for c, v in enumerate(series.values)
            if v is not None
        ]
        for run in point_runs(points, series.values):
            out.append(Polyline(tuple(run), index))
        if fmt.markers:
            out.extend(Marker(x, py, index) for x, py in points)
        for c, value in enumerate(series.values):
            if value is None:
                continue
            point_y = y(fold(value))
            top = point_y - LABEL_HEIGHT - LABEL_GAP if value >= 0 else point_y + LABEL_GAP
            out.append(
                Text(
                    plot.plot_left + c * slot,
                    top,
                    slot,
                    LABEL_HEIGHT,
                    format_value(value, fmt),
                    "center",
                    "value",
                )
            )

    centre = {c: plot.plot_left + (c + 0.5) * slot for c in range(len(data.categories))}
    for lane, arrow in enumerate(plot.brackets):
        line_y = (
            (LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0)
            + len(plot.brackets) * LANE_HEIGHT
            - lane * LANE_HEIGHT
            - LANE_LINE_GAP
        )
        out.extend(
            bracket(
                _anchor(data, centre, y, fold, arrow.start, arrow.series),
                _anchor(data, centre, y, fold, arrow.end, arrow.series),
                line_y,
                notes.label(arrow, data),
            )
        )
    for lane, arrow in enumerate(plot.levels):
        arrow_x = plot.plot_left + plot.plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(
                _level(data, centre, y, fold, arrow.start, arrow.series),
                _level(data, centre, y, fold, arrow.end, arrow.series),
                arrow_x,
                notes.label(arrow, data),
            )
        )
    for lane, annotation in enumerate(plot.value_lines):
        level = value_line.resolved(annotation, data)
        if level is None:
            continue
        line_y = y(fold(level))
        label_x = (
            plot.plot_left
            + plot.plot_width
            + (len(plot.levels) + lane) * LEVEL_LANE_WIDTH
            + LEVEL_ARROW_INSET
        )
        out.extend(
            (
                Line(plot.plot_left, line_y, plot.plot_left + plot.plot_width, line_y, "helper"),
                Text(
                    label_x,
                    line_y - LABEL_HEIGHT / 2,
                    LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
                    LABEL_HEIGHT,
                    format_value(level, fmt),
                    "left",
                    "annotation",
                ),
            )
        )
    if fmt.series_names == "labels":
        out.extend(_series_names(data, y, fold, plot.plot_left + plot.plot_width))
    return tuple(out)


def line_at(
    data: ChartData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format | None = None,
) -> tuple[int, int] | None:
    """The point (category, series) at chart point (x, y), or ``None``.

    A click near a point picks it: its centre when a marker was hit, or a label or line close to
    it. Points outside the plot or further away than :data:`PICK_TOLERANCE` hit nothing.
    """
    fmt = fmt or Format()
    plot = _plot(data, width, height, annotations, fmt)
    if (
        not data.categories
        or not data.series
        or plot.plot_width <= 0
        or plot.plot_height <= 0
        or not plot.plot_left <= x < plot.plot_left + plot.plot_width
        or not plot.top_band <= y < plot.top_band + plot.plot_height
    ):
        return None
    slot = plot.plot_width / len(data.categories)
    category = int((x - plot.plot_left) // slot)
    axis, cut = plot.axis, plot.cut
    span = axis.maximum - axis.minimum
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    scale_height = plot.plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    fold = cut.fold if cut else _same

    def point_y(value: float) -> float:
        return plot.top_band + (axis.maximum - fold(value)) / span * scale_height

    best: tuple[float, int] | None = None
    for index, series in enumerate(data.series):
        value = series.values[category]
        if value is None:
            continue
        distance = abs(y - point_y(value))
        if best is None or distance < best[0]:
            best = (distance, index)
    if best is None or best[0] > PICK_TOLERANCE:
        return None
    return category, best[1]


def _plot(
    data: ChartData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    fmt: Format,
) -> _Plot:
    brackets, levels = notes.arrows(annotations, data, "line")
    value_lines = notes.value_lines(annotations, data, "line")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes_top + lanes + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    right_lanes = len(levels) + len(value_lines)
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - right_lanes * LEVEL_LANE_WIDTH - series_band
    plot_height = height - top_band - CATEGORY_BAND
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    cut = resolve(annotations, data, "clustered")
    axis = shortened_axis(data, "clustered", cut) if cut else value_axis(data, "clustered")
    return _Plot(
        plot_left, top_band, plot_width, plot_height, axis, cut, brackets, levels, value_lines
    )


def _anchor(
    data: ChartData,
    centre: dict[int, float],
    y: _YScale,
    fold: _YScale,
    category: int,
    series: int | None,
) -> tuple[float, float]:
    value = notes.measured_value(data, category, series) or 0.0
    return centre[category], y(fold(value)) - LABEL_HEIGHT - LANE_LINE_GAP


def _level(
    data: ChartData,
    centre: dict[int, float],
    y: _YScale,
    fold: _YScale,
    category: int,
    series: int | None,
) -> tuple[float, float]:
    value = notes.measured_value(data, category, series) or 0.0
    return centre[category], y(fold(value))


def _series_names(data: ChartData, y: _YScale, fold: _YScale, band_x: float) -> list[Primitive]:
    """One series name right of the line's last point."""
    labelled: list[tuple[float, str]] = []
    for series in data.series:
        last = next(
            ((c, v) for c, v in reversed(list(enumerate(series.values))) if v is not None),
            None,
        )
        if last is None:
            continue
        _, value = last
        labelled.append((y(fold(value)) - LABEL_HEIGHT / 2, series.name))
    labelled.sort(key=lambda item: item[0], reverse=True)
    tops = spread([top for top, _ in labelled], LABEL_HEIGHT)
    return [
        Text(
            band_x + SERIES_LABEL_GAP,
            top,
            SERIES_BAND - SERIES_LABEL_GAP,
            LABEL_HEIGHT,
            name,
            "left",
            "series",
        )
        for top, (_, name) in zip(tops, labelled, strict=True)
    ]


def _same(value: float) -> float:
    return value
