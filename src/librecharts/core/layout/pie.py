"""Layout of pie and doughnut charts: one pie per category, one segment per series.

Pies sit side by side in category slots, the category name below each. Segments run clockwise from
12 o'clock in series order and show their share of the pie; negative and empty values count as
empty, like in 100 % charts. A share goes inside its segment when the segment spans at least
``MIN_INSIDE_ANGLE``, else just outside it. Which side a label is on follows from the data, never
from the size, so the primitive structure stays the same on resize (ADR 0007). A doughnut shows
the sum of its category in the hole.
"""

from __future__ import annotations

from librecharts.core.datasheet import ChartData
from librecharts.core.geometry import polar, sector
from librecharts.core.layout.common import (
    LEGEND_HEIGHT,
    SWATCH,
    SWATCH_GAP,
    format_value,
    legend,
)
from librecharts.core.model import Format
from librecharts.core.percent import column_total, share, share_label
from librecharts.core.primitives import Polygon, Primitive, Rect, Text

CATEGORY_BAND = 1000.0  # room below the pies for category names
LABEL_WIDTH = 1300.0  # width of a share or total label box
LABEL_HEIGHT = 600.0
MIN_INSIDE_ANGLE = 20.0  # degrees; narrower segments get their label outside
OUTSIDE_RADIUS = 1.15  # outside labels are centred at this multiple of the radius
INSIDE_RADIUS_PIE = 0.65  # inside labels of a pie, as a share of the radius
DOUGHNUT_HOLE = 0.5  # inner radius of a doughnut, as a share of the radius
SERIES_BAND = 2600.0  # room right of the last pie for the series names ("labels")


def layout_pie(
    data: ChartData, doughnut: bool, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the pies.
    """
    fmt = fmt or Format()
    top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    plot_width = width - band
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
    for c, category in enumerate(data.categories):
        cx = (c + 0.5) * slot
        total = column_total(data, c)
        angle = 0.0
        for index, series in enumerate(data.series):
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
                    share_label(value, total, fmt),
                    "center",
                    "value",
                    fill=index if is_inside else None,
                )
            )
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
                )
            )
        out.append(
            Text(c * slot, top + plot_height, slot, CATEGORY_BAND, category, "center", "category")
        )
    if fmt.series_names == "labels":
        out.extend(_series_names(data, plot_width, top, plot_height))
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
