"""Layout of stacked and 100 % area charts.

Every series is one filled polygon between its lower and upper cumulative edge. Negative values
count as empty, like in 100 % column charts; an empty value counts as zero so that the areas stay
closed. A 100 % area chart shows shares of the column sums. Value lines are the only annotation.

As in the column layout, the value axis is optional, the series names sit right of the last
category, and labels inside an area are left empty when the area is too flat.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    AXIS_BAND,
    LEGEND_HEIGHT,
    format_value,
    legend,
    spread,
    vertical_axis,
    vertical_grid,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.percent import column_total, share, share_label
from librecharts.core.primitives import Line, Polygon, Primitive, Text
from librecharts.core.scale import Axis, nice_axis

TOP_BAND = 800.0  # room above the plot for the highest area
LABEL_HEIGHT = 600.0  # height of a value or series name box
CATEGORY_BAND = 1000.0  # room below the plot for category names
MIN_SEGMENT_FOR_LABEL = 500.0  # flatter areas get no inside label
LEVEL_LANE_WIDTH = 2000.0  # room right of the plot for one value line and its label
LEVEL_ARROW_INSET = 300.0  # from a lane's left edge to its line's label
LEVEL_LABEL_GAP = 150.0  # between a value line and its label
SERIES_BAND = 2600.0  # room right of the lanes for series names
SERIES_LABEL_GAP = 150.0  # between the lanes and a series name

PERCENT_AXIS = Axis(0.0, 100.0, 20.0)  # the fixed scale of a 100 % area chart

_YScale = Callable[[float], float]


def layout_area(
    data: ChartData,
    grouping: str,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    percent: bool = False,
    fmt: Format | None = None,
    length_per_unit: float | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    ``grouping`` has no meaning for areas and is accepted for a uniform layout signature. With
    ``percent`` the areas are shares of the column sums and no annotations are drawn.
    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm and
    anchors the scale at the plot bottom.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    value_lines = [] if percent else notes.value_lines(annotations, data, "area")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = lanes_top + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    right_lanes = len(value_lines)
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - right_lanes * LEVEL_LANE_WIDTH - series_band
    plot_height = height - top_band - CATEGORY_BAND
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    axis = PERCENT_AXIS if percent else _value_axis(data)
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        if length_per_unit is not None:
            return top_band + plot_height - (value - axis.minimum) * length_per_unit
        return top_band + (axis.maximum - value) / span * plot_height

    slot = plot_width / len(data.categories)
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    out.append(Line(plot_left, y(0), plot_left + plot_width, y(0), "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(vertical_grid(axis, None, y, plot_left, plot_width))
        out.extend(vertical_axis(axis, None, y, plot_left, fmt))
    for c, category in enumerate(data.categories):
        out.append(
            Text(
                plot_left + c * slot,
                top_band + plot_height,
                slot,
                CATEGORY_BAND,
                category,
                "center",
                "category",
            )
        )

    totals = [column_total(data, c) for c in range(len(data.categories))]
    lower = [0.0] * len(data.categories)
    for index, series in enumerate(data.series):
        upper = [
            lower[c] + _height(series.values[c], totals[c], percent) for c in range(len(totals))
        ]
        if any(not _same(upper[c], lower[c]) for c in range(len(totals))):
            points = [(plot_left + (c + 0.5) * slot, y(upper[c])) for c in range(len(totals))] + [
                (plot_left + (c + 0.5) * slot, y(lower[c])) for c in reversed(range(len(totals)))
            ]
            out.append(Polygon(tuple(points), index))
            for c in range(len(totals)):
                height = y(lower[c]) - y(upper[c])
                label = ""
                if height >= MIN_SEGMENT_FOR_LABEL:
                    label = (
                        share_label(series.values[c], totals[c], fmt)
                        if percent
                        else format_value(series.values[c] or 0.0, fmt)
                    )
                out.append(
                    Text(
                        plot_left + c * slot,
                        (y(upper[c]) + y(lower[c])) / 2 - LABEL_HEIGHT / 2,
                        slot,
                        LABEL_HEIGHT,
                        label,
                        "center",
                        "value",
                        fill=index,
                    )
                )
        lower = upper

    for lane, annotation in enumerate(value_lines):
        level = value_line.resolved(annotation, data)
        if level is None:
            continue
        line_y = y(level)
        label_x = plot_left + plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            (
                Line(plot_left, line_y, plot_left + plot_width, line_y, "helper"),
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
        out.extend(_series_names(data, totals, y, plot_left + plot_width, percent))
    return tuple(out)


def natural_length_per_unit(
    data: ChartData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    percent: bool = False,
    fmt: Format | None = None,
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size."""
    if percent:
        return None
    fmt = fmt or Format()
    value_lines = notes.value_lines(annotations, data, "area")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = lanes_top + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - plot_left - len(value_lines) * LEVEL_LANE_WIDTH - series_band
    plot_height = height - top_band - CATEGORY_BAND
    if plot_width <= 0 or plot_height <= 0 or not data.categories or not data.series:
        return None
    axis = _value_axis(data)
    span = axis.maximum - axis.minimum
    if span <= 0:
        return None
    return plot_height / span


def _height(value: float | None, total: float, percent: bool) -> float:
    """The vertical contribution of one value: negative and empty values count as zero."""
    if percent:
        return share(value, total) or 0.0
    return value if value is not None and value > 0 else 0.0


def _value_axis(data: ChartData) -> Axis:
    """0..the highest stack of positive values."""
    totals = [
        sum(v for s in data.series if (v := s.values[c]) is not None and v > 0)
        for c in range(len(data.categories))
    ]
    return nice_axis(0.0, max(totals, default=0.0))


def _series_names(
    data: ChartData,
    totals: list[float],
    y: _YScale,
    band_x: float,
    percent: bool,
) -> list[Primitive]:
    """One series name per area, level with the last category's segment."""
    last = len(data.categories) - 1
    labelled: list[tuple[float, str]] = []
    lower = 0.0
    for series in data.series:
        upper = lower + _height(series.values[last], totals[last], percent)
        labelled.append(((y(upper) + y(lower)) / 2 - LABEL_HEIGHT / 2, series.name))
        lower = upper
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


def _same(first: float, second: float) -> bool:
    return abs(first - second) < 1e-9
