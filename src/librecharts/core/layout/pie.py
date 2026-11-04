"""Layout of pie and doughnut charts: one pie per category, one segment per series.

Pies sit side by side in category slots, the category name below each. Segments run clockwise from
12 o'clock in series order and show their share of the pie; negative and empty values count as
empty, like in 100 % charts. A share goes inside its segment when the segment spans at least
``MIN_INSIDE_ANGLE``, else just outside it. Which side a label is on follows from the data, never
from the size, so the primitive structure stays the same on resize (ADR 0007). A doughnut shows
the sum of its category in the hole.

Annotations (M14): difference and CAGR arrows between two segments (of one pie or of two), labelled
with the segments' shares, so an absolute difference reads as percentage points. Bracket arrows run
in lanes above the pies and meet the arcs of the segments they measure at their mid-angle; level
arrows run in lanes right of the pies.
"""

from __future__ import annotations

import math

from librecharts.core import annotations as notes
from librecharts.core.datasheet import ChartData
from librecharts.core.geometry import polar, sector
from librecharts.core.layout.column import LANE_HEIGHT, LANE_LINE_GAP
from librecharts.core.layout.common import (
    LABEL_HEIGHT,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LANE_WIDTH,
    SWATCH,
    SWATCH_GAP,
    bracket,
    format_value,
    legend,
    level_arrow,
)
from librecharts.core.model import Annotation, Format, LabelKey, SortOrder
from librecharts.core.percent import column_total, share, shares
from librecharts.core.primitives import Polygon, Primitive, Rect, Text
from librecharts.core.rounding import consistent_shares
from librecharts.core.sorting import pie_order

CATEGORY_BAND = 1000.0  # room below the pies for category names
LABEL_WIDTH = 1300.0  # width of a share or total label box
MIN_INSIDE_ANGLE = 20.0  # degrees; narrower segments get their label outside
OUTSIDE_RADIUS = 1.15  # outside labels are centred at this multiple of the radius
INSIDE_RADIUS_PIE = 0.65  # inside labels of a pie, as a share of the radius
DOUGHNUT_HOLE = 0.5  # inner radius of a doughnut, as a share of the radius
SERIES_BAND = 2600.0  # room right of the last pie for the series names ("labels")


def layout_pie(
    data: ChartData,
    doughnut: bool,
    width: float,
    height: float,
    fmt: Format | None = None,
    annotations: tuple[Annotation, ...] = (),
    sort: SortOrder = "none",
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``sort`` the segments of each pie run in that order (largest first for ``descending``);
    it is a display order only, labels and arrows keep their data sheet series indices.

    Raises ``ValueError`` if the box leaves no room for the pies.
    """
    fmt = fmt or Format()
    arrow_data = shares(data)
    brackets, levels = notes.arrows(annotations, arrow_data, "pie")
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top = legend_band + len(brackets) * LANE_HEIGHT
    right_lanes = len(levels) * LEVEL_LANE_WIDTH
    band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - band - right_lanes
    plot_height = height - top - CATEGORY_BAND
    slot = plot_width / max(len(data.categories), 1)
    # The outside labels must fit into the slot: they reach 1.15 r plus half a label box.
    radius = (min(slot, plot_height) / 2 - LABEL_WIDTH / 2) / OUTSIDE_RADIUS
    if radius <= 0:
        raise ValueError("chart area too small")
    if not data.categories or not data.series:
        return ()

    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    inner = radius * DOUGHNUT_HOLE if doughnut else 0.0
    inside = radius * ((1 + DOUGHNUT_HOLE) / 2 if doughnut else INSIDE_RADIUS_PIE)
    cy = top + plot_height / 2
    arcs: dict[tuple[int, int], tuple[float, float]] = {}  # (category, series) -> arc midpoint
    orders = pie_order(data, sort)
    for c, category in enumerate(data.categories):
        cx = (c + 0.5) * slot
        total = column_total(data, c)
        percentages = consistent_shares([series.values[c] for series in data.series], total, fmt)
        angle = 0.0
        for index in orders[c]:
            series = data.series[index]
            value = series.values[c]
            if value is None or share(value, total) is None:
                continue
            sweep = value / total * 360.0
            out.append(Polygon(sector(cx, cy, radius, inner, angle, angle + sweep), index))
            is_inside = sweep >= MIN_INSIDE_ANGLE
            label_radius = inside if is_inside else radius * OUTSIDE_RADIUS
            label_x, label_y = polar(cx, cy, label_radius, angle + sweep / 2)
            out.append(
                Text(
                    label_x - LABEL_WIDTH / 2,
                    label_y - LABEL_HEIGHT / 2,
                    LABEL_WIDTH,
                    LABEL_HEIGHT,
                    percentages[index] or "",
                    "center",
                    "value",
                    fill=index if is_inside else None,
                    key=LabelKey("value", c, index),
                )
            )
            arcs[(c, index)] = polar(cx, cy, radius, angle + sweep / 2)
            angle += sweep
        if doughnut and total > 0:
            out.append(
                Text(
                    cx - inner,
                    cy - LABEL_HEIGHT / 2,
                    2 * inner,
                    LABEL_HEIGHT,
                    format_value(total, fmt),
                    "center",
                    "total",
                    key=LabelKey("total", c),
                )
            )
        out.append(
            Text(c * slot, top + plot_height, slot, CATEGORY_BAND, category, "center", "category")
        )

    def end_series(arrow: Annotation) -> int | None:
        """The series the arrow's end measures: its own, or the start's when it has none."""
        return arrow.series_end if arrow.series_end is not None else arrow.series

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where an arrow meets what it measures: a segment's arc, or the top of the pie."""
        if series is None:
            return (category + 0.5) * slot, cy - radius
        return arcs.get((category, series), ((category + 0.5) * slot, cy))

    for lane, arrow in enumerate(brackets):
        line_y = legend_band + len(brackets) * LANE_HEIGHT - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, end_series(arrow)),
                line_y,
                notes.label(arrow, arrow_data),
            )
        )
    for lane, arrow in enumerate(levels):
        arrow_x = plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, end_series(arrow)),
                arrow_x,
                notes.label(arrow, arrow_data),
            )
        )
    if fmt.series_names == "labels":
        out.extend(_series_names(data, plot_width + right_lanes, top, plot_height))
    return tuple(out)


def _series_names(data: ChartData, left: float, top: float, plot_height: float) -> list[Primitive]:
    """A legend column right of the last pie, centred vertically."""
    first = top + (plot_height - len(data.series) * LABEL_HEIGHT) / 2
    out: list[Primitive] = []
    for index, series in enumerate(data.series):
        y = first + index * LABEL_HEIGHT
        out.append(Rect(left, y + (LABEL_HEIGHT - SWATCH) / 2, SWATCH, SWATCH, index))
        out.append(
            Text(
                left + SWATCH + SWATCH_GAP,
                y,
                SERIES_BAND - SWATCH - SWATCH_GAP,
                LABEL_HEIGHT,
                series.name,
                "left",
                "series",
            )
        )
    return out


def pie_at(
    data: ChartData,
    doughnut: bool,
    width: float,
    height: float,
    x: float,
    y: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
    sort: SortOrder = "none",
) -> tuple[int, int | None] | None:
    """The segment at chart point (x, y): (category, series), or ``None``.

    Uses the geometry of :func:`layout_pie`; a click between the pies, outside them, in the hole
    of a doughnut or in the annotation lanes hits nothing.
    """
    fmt = fmt or Format()
    arrow_data = shares(data)
    brackets, levels = notes.arrows(annotations, arrow_data, "pie")
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top = legend_band + len(brackets) * LANE_HEIGHT
    right_lanes = len(levels) * LEVEL_LANE_WIDTH
    band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - band - right_lanes
    plot_height = height - top - CATEGORY_BAND
    slot = plot_width / max(len(data.categories), 1)
    radius = (min(slot, plot_height) / 2 - LABEL_WIDTH / 2) / OUTSIDE_RADIUS
    if radius <= 0 or not data.categories or not data.series or not 0 <= x < plot_width:
        return None
    category = int(x // slot)
    if category >= len(data.categories):
        return None
    cx, cy = (category + 0.5) * slot, top + plot_height / 2
    dx, dy = x - cx, y - cy
    distance = math.hypot(dx, dy)
    inner = radius * (DOUGHNUT_HOLE if doughnut else 0.0)
    if not inner <= distance <= radius:
        return None
    # clockwise from 12 o'clock; ``-dy if dy else 0.0`` keeps the centre out of -0.0, where
    # atan2 would put it at 180 degrees
    angle = math.degrees(math.atan2(dx, -dy if dy else 0.0)) % 360
    total = column_total(data, category)
    walked = 0.0
    for index in pie_order(data, sort)[category]:
        series = data.series[index]
        value = series.values[category]
        if value is None or share(value, total) is None:
            continue
        sweep = value / total * 360.0
        if walked <= angle < walked + sweep:
            return category, index
        walked += sweep
    return None
