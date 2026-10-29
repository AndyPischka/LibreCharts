"""Layout of butterfly charts: two series as bars mirrored around a central band of category names.

The first series grows to the left, the second to the right, both on one scale (the larger maximum
of the two), so lengths compare across the centre. Further series are ignored. Negative and empty
values draw no bar and no label. Value labels sit at the bar ends, the series names above each
half. Categories run top to bottom in display order (the layout gets them already sorted).

A value axis (tick labels below each half) and gridlines are optional. The primitive structure
depends on the data and the format only, never on the size (ADR 0007).
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import (
    GAP_RATIO,
    LEGEND_HEIGHT,
    SWATCH,
    SWATCH_GAP,
    TICK_GAP,
    TICK_HEIGHT,
    format_value,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Align, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, nice_axis

CENTER_BAND = 3000.0  # width of the band between the halves, for the category names
LABEL_WIDTH = 1200.0  # width of a value label box
LABEL_GAP = 150.0  # between a bar end and its label
OUTER_BAND = LABEL_WIDTH + LABEL_GAP  # room outside each half for the label of the longest bar
LABEL_HEIGHT = 600.0
AXIS_BAND_HEIGHT = 700.0  # room below the plot for tick labels
TICK_WIDTH = 1600.0


def layout_butterfly(
    data: ChartData,
    width: float,
    height: float,
    fmt: Format | None = None,
    length_per_unit: float | None = None,
) -> tuple[Primitive, ...]:
    """Lay out the first two series of ``data`` into a ``width`` x ``height`` box.

    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm.

    Raises ``ValueError`` if the box leaves no room for the bars.
    """
    fmt = fmt or Format()
    half = _half_width(width)
    plot_top = LEGEND_HEIGHT
    plot_height = height - plot_top - (AXIS_BAND_HEIGHT if fmt.axis else 0.0)
    if half <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    sides = data.series[:2]
    axis = _scale_axis(data)
    left_zero = OUTER_BAND + half  # x of the left baseline: left bars grow from here to the left
    right_zero = left_zero + CENTER_BAND

    def length(value: float) -> float:
        if length_per_unit is not None:
            return value * length_per_unit
        return value / axis.maximum * half

    plot_bottom = plot_top + plot_height
    out: list[Primitive] = []
    for side, series in enumerate(sides):  # series names above the halves, next to a colour swatch
        out.extend(_header(series.name, side, side, left_zero, right_zero, half))
    out.append(Line(left_zero, plot_top, left_zero, plot_bottom, "baseline"))
    out.append(Line(right_zero, plot_top, right_zero, plot_bottom, "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(_grid(axis, length, left_zero, right_zero, plot_top, plot_bottom))
        out.extend(_ticks(axis, length, left_zero, right_zero, plot_bottom, fmt))

    slot = plot_height / len(data.categories)
    thickness = slot * (1 - GAP_RATIO)
    for c, category in enumerate(data.categories):
        slot_y = plot_top + c * slot
        bar_y = slot_y + (slot - thickness) / 2
        out.append(Text(left_zero, slot_y, CENTER_BAND, slot, category, "center", "category"))
        for side, series in enumerate(sides):
            value = series.values[c]
            if value is None or value <= 0:
                continue
            bar = length(value)
            align: Align
            if side == 0:
                out.append(Rect(left_zero - bar, bar_y, bar, thickness, 0))
                label_x, align = left_zero - bar - LABEL_GAP - LABEL_WIDTH, "right"
            else:
                out.append(Rect(right_zero, bar_y, bar, thickness, 1))
                label_x, align = right_zero + bar + LABEL_GAP, "left"
            out.append(
                Text(
                    label_x,
                    bar_y,
                    LABEL_WIDTH,
                    thickness,
                    format_value(value, fmt),
                    align,
                    "value",
                )
            )
    return tuple(out)


def natural_length_per_unit(
    data: ChartData, width: float, height: float, fmt: Format | None = None
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size."""
    fmt = fmt or Format()
    half = _half_width(width)
    plot_height = height - LEGEND_HEIGHT - (AXIS_BAND_HEIGHT if fmt.axis else 0.0)
    if half <= 0 or plot_height <= 0 or not data.categories or not data.series:
        return None
    return half / _scale_axis(data).maximum


def _half_width(width: float) -> float:
    """The room for the bars of one half."""
    return (width - CENTER_BAND) / 2 - OUTER_BAND


def _scale_axis(data: ChartData) -> Axis:
    """The common axis of both halves: from zero to the larger maximum."""
    values = [v for s in data.series[:2] for v in s.values if v is not None and v > 0]
    return nice_axis(0.0, max(values, default=0.0))


def _header(
    name: str, side: int, series: int, left_zero: float, right_zero: float, half: float
) -> list[Primitive]:
    """A series name above its half, with a swatch of the series colour next to the centre."""
    top = (LEGEND_HEIGHT - SWATCH) / 2
    text_width = max(half - SWATCH - SWATCH_GAP, 0.0)
    if side == 0:  # right-aligned against the centre, swatch on its right
        return [
            Rect(left_zero - SWATCH, top, SWATCH, SWATCH, series),
            Text(
                left_zero - SWATCH - SWATCH_GAP - text_width,
                top,
                text_width,
                SWATCH,
                name,
                "right",
                "series",
            ),
        ]
    return [
        Rect(right_zero, top, SWATCH, SWATCH, series),
        Text(right_zero + SWATCH + SWATCH_GAP, top, text_width, SWATCH, name, "left", "series"),
    ]


def _grid(
    axis: Axis,
    length: Callable[[float], float],
    left_zero: float,
    right_zero: float,
    plot_top: float,
    plot_bottom: float,
) -> list[Primitive]:
    """Light vertical lines at every tick above zero, in both halves."""
    return [
        Line(base + sign * length(tick), plot_top, base + sign * length(tick), plot_bottom, "grid")
        for base, sign in ((left_zero, -1), (right_zero, 1))
        for tick in axis.ticks()
        if tick > 0
    ]


def _ticks(
    axis: Axis,
    length: Callable[[float], float],
    left_zero: float,
    right_zero: float,
    plot_bottom: float,
    fmt: Format,
) -> list[Primitive]:
    """An axis line under each half with its tick labels (both count up from the centre)."""
    out: list[Primitive] = []
    for base, sign in ((left_zero, -1), (right_zero, 1)):
        end = base + sign * length(axis.maximum)
        out.append(Line(min(base, end), plot_bottom, max(base, end), plot_bottom, "axis"))
        out.extend(
            Text(
                base + sign * length(tick) - TICK_WIDTH / 2,
                plot_bottom + TICK_GAP,
                TICK_WIDTH,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "center",
                "axis",
            )
            for tick in axis.ticks()
        )
    return out
