# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Turn layout primitives into native Draw shapes inside one group shape (ADR 0002).

Every group starts with an invisible frame rectangle spanning the whole layout box. It keeps the
group's bounding box equal to the layout size, so re-rendering at the group's current size is
stable even when labels or bars do not reach the edges.
"""

from __future__ import annotations

from typing import Any

import uno
from com.sun.star.awt import Point, Size

from librecharts.core.primitives import Line, Primitive, Rect, Text

PALETTE = (0x8FB4E3, 0x5E8AC7, 0xC9D8EE, 0xA6A6A6, 0xF4B183, 0xD9D9D9)
TEXT_COLOR = 0x000000
LINE_COLOR = 0x404040
LINE_WIDTH = 25  # 1/100 mm
FONT_HEIGHT_PT = 10.0

_FILL_NONE = uno.Enum("com.sun.star.drawing.FillStyle", "NONE")
_FILL_SOLID = uno.Enum("com.sun.star.drawing.FillStyle", "SOLID")
_LINE_NONE = uno.Enum("com.sun.star.drawing.LineStyle", "NONE")
_LINE_SOLID = uno.Enum("com.sun.star.drawing.LineStyle", "SOLID")
_V_CENTER = uno.Enum("com.sun.star.drawing.TextVerticalAdjust", "CENTER")
_H_BLOCK = uno.Enum("com.sun.star.drawing.TextHorizontalAdjust", "BLOCK")
_PARA_ADJUST = {
    "left": uno.Enum("com.sun.star.style.ParagraphAdjust", "LEFT"),
    "center": uno.Enum("com.sun.star.style.ParagraphAdjust", "CENTER"),
    "right": uno.Enum("com.sun.star.style.ParagraphAdjust", "RIGHT"),
}


def render_group(
    doc: Any, page: Any, primitives: tuple[Primitive, ...], x: int, y: int, width: int, height: int
) -> Any:
    """Create a new group at (``x``, ``y``) on ``page`` holding the frame and ``primitives``."""
    group = doc.createInstance("com.sun.star.drawing.GroupShape")
    page.add(group)
    _add_children(doc, group, primitives, x, y, width, height)
    return group


def rerender(doc: Any, group: Any, primitives: tuple[Primitive, ...]) -> None:
    """Replace the group's children; position, size, name and z-order of the group are kept.

    ``primitives`` must have been laid out for the group's current size.
    """
    old = [group.getByIndex(i) for i in range(group.getCount())]
    position, size = group.Position, group.Size
    # Add first, then remove: an emptied group may be dissolved by LibreOffice.
    _add_children(doc, group, primitives, position.X, position.Y, size.Width, size.Height)
    for shape in old:
        group.remove(shape)


def _add_children(
    doc: Any,
    group: Any,
    primitives: tuple[Primitive, ...],
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    frame = _add(doc, group, "RectangleShape", x, y, width, height)
    frame.FillStyle, frame.LineStyle = _FILL_NONE, _LINE_NONE
    for p in primitives:
        if isinstance(p, Rect):
            shape = _add(doc, group, "RectangleShape", x + p.x, y + p.y, p.width, p.height)
            shape.FillStyle, shape.FillColor = _FILL_SOLID, PALETTE[p.series % len(PALETTE)]
            shape.LineStyle = _LINE_NONE
        elif isinstance(p, Line):
            shape = _add(doc, group, "LineShape", x + p.x1, y + p.y1, p.x2 - p.x1, p.y2 - p.y1)
            shape.LineStyle, shape.LineColor, shape.LineWidth = _LINE_SOLID, LINE_COLOR, LINE_WIDTH
        else:
            _add_text(doc, group, p, x, y)


def _add_text(doc: Any, group: Any, p: Text, x: int, y: int) -> None:
    shape = _add(doc, group, "TextShape", x + p.x, y + p.y, p.width, p.height)
    shape.TextAutoGrowHeight = False
    shape.TextAutoGrowWidth = False
    shape.TextVerticalAdjust = _V_CENTER
    shape.TextHorizontalAdjust = _H_BLOCK
    shape.TextLeftDistance = shape.TextRightDistance = 0
    shape.TextUpperDistance = shape.TextLowerDistance = 0
    # Text and character properties only stick once the shape is in a group or on a page.
    shape.String = p.text
    shape.CharHeight = FONT_HEIGHT_PT
    shape.CharColor = TEXT_COLOR
    shape.ParaAdjust = _PARA_ADJUST[p.align]


def _add(doc: Any, group: Any, kind: str, x: float, y: float, width: float, height: float) -> Any:
    shape = doc.createInstance(f"com.sun.star.drawing.{kind}")
    group.add(shape)
    shape.Position = Point(round(x), round(y))
    shape.Size = Size(max(round(width), 0), max(round(height), 0))
    return shape
