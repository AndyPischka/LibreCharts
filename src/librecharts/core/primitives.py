"""Drawing primitives produced by layout: plain geometry, no styling and no UNO.

Units are 1/100 mm (Draw's native unit), origin at the top-left of the chart, y grows downwards.
Colours, fonts and line widths are decided by the renderer from the ``series`` and ``role`` fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TextRole = Literal["value", "total", "category"]
LineRole = Literal["baseline"]
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
    x1: float
    y1: float
    x2: float
    y2: float
    role: LineRole


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
