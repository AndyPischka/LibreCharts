"""Layout of line charts.

One line per series through the category slots, with point markers, a value label at every point
and the series name right of its last point. An empty value splits a series into several lines, so
the primitive structure depends on the data and the format only, never on the size. With
``interpolate`` an empty value is bridged linearly between its neighbouring known points instead:
the series stays one polyline, the bridged points get no marker and no label, and leading or
trailing gaps are never extrapolated. Interpolation changes only coordinates, never which
primitives exist for a given data set, so the structure still never depends on the size.

As in the column layout, a value axis is optional; arrows (difference, CAGR) run in lanes above the
plot, level arrows and value lines in lanes right of it. An axis break shortens the value scale.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import cast

from librecharts.core import annotations as notes
from librecharts.core import trend as trends_module
from librecharts.core import value_line
from librecharts.core.axis_break import Break, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData, with_error_margins
from librecharts.core.layout.common import (
    AXIS_BAND,
    AXIS_TITLE_BAND,
    LABEL_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    axis_title,
    baseline_cut,
    bracket,
    category_title,
    format_value,
    legend,
    legend_insets,
    level_arrow,
    point_runs,
    spread,
    value_axis,
    vertical_axis,
    vertical_grid,
)
from librecharts.core.model import Annotation, Format, LabelKey, Trend
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
ERROR_CAP = 150.0  # half the width of an error bar's cap, 1/100 mm
TREND_LABEL_GAP = 150.0  # between a trendline's end and its R² label
TREND_LABEL_WIDTH = 3000.0

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
    length_per_unit: float | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
    trends: tuple[Trend, ...] = (),
    interpolate: bool = False,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``errors`` every point gets a whisker with caps at value ± ``errors[i][c]``; the scale
    covers value ± error as well. With ``interpolate`` empty values are bridged linearly (M32).

    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm and
    anchors the scale at the plot bottom; an axis break is then ignored.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    plot = _plot(data, width, height, annotations, fmt, length_per_unit, errors)
    if not data.categories or not data.series:
        return ()

    axis, cut = plot.axis, plot.cut
    span = axis.maximum - axis.minimum
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    scale_height = plot.plot_height - (LABEL_HEIGHT if has_negative else 0.0)

    def y(value: float) -> float:
        if length_per_unit is not None:
            return plot.top_band + scale_height - (value - axis.minimum) * length_per_unit
        if axis.scale == "log":
            if value <= 0:
                return plot.top_band + scale_height
            return plot.top_band + (1.0 - axis.fraction(fold(value))) * scale_height
        return plot.top_band + (axis.maximum - value) / span * scale_height

    fold = cut.fold if cut else _same
    extra = max((item.forecast for item in trends), default=0)
    slot = plot.plot_width / (len(data.categories) + extra)
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width, fmt.legend, height))
    out.append(Line(plot.plot_left, y(0), plot.plot_left + plot.plot_width, y(0), "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(vertical_grid(axis, cut, y, plot.plot_left, plot.plot_width))
        out.extend(vertical_axis(axis, cut, y, plot.plot_left, fmt))
    if fmt.axis_title:
        out.extend(axis_title(fmt, 0.0, plot.top_band, AXIS_TITLE_BAND, scale_height, rotated=True))
    if fmt.category_axis_title:
        out.extend(
            category_title(
                fmt,
                plot.plot_left,
                plot.top_band + plot.plot_height + CATEGORY_BAND,
                plot.plot_width,
            )
        )
    if axis.minimum > 0:
        out.extend(baseline_cut(plot.plot_left, plot.top_band + scale_height))

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

    above: dict[int, list[tuple[float, int, str]]] = {}
    for index, series in enumerate(data.series):
        drawn = _interpolated(series.values) if interpolate else series.values
        points = [
            (plot.plot_left + (c + 0.5) * slot, y(fold(v)))
            for c, v in enumerate(drawn)
            if v is not None
        ]
        for run in point_runs(points, drawn):
            out.append(Polyline(tuple(run), index))
        real = [(c, v) for c, v in enumerate(series.values) if v is not None]
        if fmt.markers:
            # only real points get a marker, never a bridged gap (M32)
            out.extend(
                Marker(plot.plot_left + (c + 0.5) * slot, y(fold(v)), index, category=c)
                for c, v in real
            )
        for c, value in enumerate(series.values):
            if value is None:
                continue
            point_y = y(fold(value))
            if value >= 0:
                # Labels above their point are collected and moved apart after the loop, so that
                # the labels of several series at one category do not overlap (M16 decluttering).
                above.setdefault(c, []).append(
                    (point_y - LABEL_HEIGHT - LABEL_GAP, index, format_value(value, fmt))
                )
            else:
                out.append(
                    Text(
                        plot.plot_left + c * slot,
                        point_y + LABEL_GAP,
                        slot,
                        LABEL_HEIGHT,
                        format_value(value, fmt),
                        "center",
                        "value",
                        key=LabelKey("value", c, index),
                    )
                )
            if errors is not None:
                err = errors[index][c] if index < len(errors) else None
                if err:
                    cx = plot.plot_left + (c + 0.5) * slot
                    y_top, y_bottom = y(fold(value + err)), y(fold(value - err))
                    out.extend(
                        (
                            Line(cx, y_top, cx, y_bottom, "annotation"),
                            Line(cx - ERROR_CAP, y_top, cx + ERROR_CAP, y_top, "annotation"),
                            Line(cx - ERROR_CAP, y_bottom, cx + ERROR_CAP, y_bottom, "annotation"),
                        )
                    )

    for c in range(len(data.categories)):
        entries = sorted(above.get(c, ()), key=lambda entry: -entry[0])  # bottom-up
        tops = spread([entry[0] for entry in entries], LABEL_HEIGHT)
        for (_, index, text), top in zip(entries, tops, strict=True):
            out.append(
                Text(
                    plot.plot_left + c * slot,
                    top,
                    slot,
                    LABEL_HEIGHT,
                    text,
                    "center",
                    "value",
                    key=LabelKey("value", c, index),
                )
            )

    centre = {c: plot.plot_left + (c + 0.5) * slot for c in range(len(data.categories))}
    for lane, arrow in enumerate(plot.brackets):
        line_y = (
            legend_insets(fmt)[1]
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
    for item in trends:
        if item.series >= len(data.series):
            continue
        points = trends_module.points_of(data.series[item.series].values)
        try:
            fitted = trends_module.fit(points, item.kind)
        except ValueError:
            fitted = None
        if fitted is None:
            continue
        first, last = points[0][0], points[-1][0]
        end = last + item.forecast
        start_point = (plot.plot_left + (first + 0.5) * slot, y(fold(fitted.value(first))))
        end_point = (plot.plot_left + (last + 0.5) * slot, y(fold(fitted.value(last))))
        out.append(Polyline((start_point, end_point), item.series))
        label_x = end_point[0]
        label_y = end_point[1]
        if end > last:
            forecast_point = (plot.plot_left + (end + 0.5) * slot, y(fold(fitted.value(end))))
            out.append(Polyline((end_point, forecast_point), item.series, dashed=True))
            label_x, label_y = forecast_point
        if item.show_r2 or item.show_equation:
            out.append(
                Text(
                    label_x + TREND_LABEL_GAP,
                    label_y - LABEL_HEIGHT / 2,
                    TREND_LABEL_WIDTH,
                    LABEL_HEIGHT,
                    trends_module.label(fitted, fmt, equation=item.show_equation),
                    "left",
                    "annotation",
                )
            )
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
    length_per_unit: float | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
) -> _Plot:
    brackets, levels = notes.arrows(annotations, data, "line")
    value_lines = notes.value_lines(annotations, data, "line")
    inset_left, lanes_top, inset_right, inset_bottom = legend_insets(fmt)
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes_top + lanes + TOP_BAND
    title_band = AXIS_TITLE_BAND if fmt.axis_title else 0.0
    category_band = AXIS_TITLE_BAND if fmt.category_axis_title else 0.0
    plot_left = inset_left + title_band + (AXIS_BAND if fmt.axis else 0.0)
    right_lanes = len(levels) + len(value_lines)
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - inset_right - right_lanes * LEVEL_LANE_WIDTH - series_band
    plot_height = height - top_band - inset_bottom - CATEGORY_BAND - category_band
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    scale_data = with_error_margins(data, errors) if errors is not None else data
    cut = None if length_per_unit is not None else resolve(annotations, scale_data, "clustered")
    axis = (
        shortened_axis(scale_data, "clustered", cut)
        if cut
        else value_axis(scale_data, "clustered", fmt, include_zero=fmt.axis_scale != "log")
    )
    return _Plot(
        plot_left, top_band, plot_width, plot_height, axis, cut, brackets, levels, value_lines
    )


def natural_length_per_unit(
    data: ChartData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size."""
    try:
        plot = _plot(data, width, height, annotations, fmt or Format(), errors=errors)
    except ValueError:
        return None
    span = plot.axis.maximum - plot.axis.minimum
    if span <= 0 or not data.categories or not data.series:
        return None
    has_negative = any(v is not None and v < 0 for s in data.series for v in s.values)
    return (plot.plot_height - (LABEL_HEIGHT if has_negative else 0.0)) / span


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


def _interpolated(values: Sequence[float | None]) -> list[float | None]:
    """``values`` with every interior gap filled linearly between its known neighbours (M32).

    Leading and trailing gaps stay empty: the line is never extrapolated. The result drives only
    the polyline's points; markers, labels, error bars and trendlines keep the real values.
    """
    filled = list(values)
    known = [c for c, value in enumerate(values) if value is not None]
    for left, right in pairwise(known):
        if right > left + 1:
            start, end = cast("float", values[left]), cast("float", values[right])
            for c in range(left + 1, right):
                filled[c] = start + (end - start) * (c - left) / (right - left)
    return filled


def _same(value: float) -> float:
    return value
