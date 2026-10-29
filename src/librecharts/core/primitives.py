"""Drawing primitives produced by layout: plain geometry, no styling and no UNO.

Units are 1/100 mm (Draw's native unit), origin at the top-left of the chart, y grows downwards.
Colours, fonts and line widths are decided by the renderer from the ``series`` and ``role`` fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TextRole = Literal["value", "total", "category", "series", "annotation", "axis"]
LineRole = Literal["baseline", "connector", "annotation", "helper", "axis", "grid"]
Align = Literal["left", "center", "right"]


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float
    series: int  # index into ChartData.series, selects the fill colour; BACKGROUND: none


BACKGROUND = -1  # Rect.series of gaps cut into other shapes (axis breaks): slide background


@dataclass(frozen=True, slots=True)
class Line:
    """A line from (x1, y1) to (x2, y2).

    Lines are horizontal, vertical, or run from top-left to bottom-right: the renderer draws them
    by their bounding box. ``helper`` lines are dashed.
    """

    x1: float
    y1: float
    x2: float
    y2: float
    role: LineRole
    arrow: bool = False  # arrowhead at (x2, y2)


@dataclass(frozen=True, slots=True)
class Text:
    """A text box; the renderer centres the text vertically inside it.

    ``fill`` is the series index of the rectangle behind the text, if any. The renderer then picks
    black or white text for contrast (``core/style.py``).
    """

    x: float
    y: float
    width: float
    height: float
    text: str
    align: Align
    role: TextRole
    fill: int | None = None


@dataclass(frozen=True, slots=True)
class Polyline:
    """A connected line through ``points`` (diagonal segments allowed).

    One primitive per run of consecutive values, so a series stays one selectable shape. The
    renderer draws it in the series colour.
    """

    points: tuple[tuple[float, float], ...]
    series: int


@dataclass(frozen=True, slots=True)
class Polygon:
    """A closed, filled area through ``points``, in the series colour (stacked area charts)."""

    points: tuple[tuple[float, float], ...]
    series: int


@dataclass(frozen=True, slots=True)
class Marker:
    """A small filled circle at (``x``, ``y``) in the series colour (line points)."""

    x: float
    y: float
    series: int


MARKER_SIZE = 250.0  # diameter of a point marker, 1/100 mm; the renderer keeps it fixed on resize

Primitive = Rect | Line | Text | Polyline | Polygon | Marker
