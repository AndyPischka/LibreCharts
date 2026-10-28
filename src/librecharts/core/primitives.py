"""Drawing primitives produced by layout: plain geometry, no styling and no UNO.

Units are 1/100 mm (Draw's native unit), origin at the top-left of the chart, y grows downwards.
Colours, fonts and line widths are decided by the renderer from the ``series`` and ``role`` fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TextRole = Literal["value", "total", "category", "series", "annotation"]
LineRole = Literal["baseline", "connector", "annotation", "helper"]
Align = Literal["left", "center", "right"]


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float
    series: int  # index into ChartData.series, selects the fill colour


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
    """A text box; the renderer centres the text vertically inside it."""

    x: float
    y: float
    width: float
    height: float
    text: str
    align: Align
    role: TextRole


Primitive = Rect | Line | Text
