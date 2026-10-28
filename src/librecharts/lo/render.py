# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Turn layout primitives into native Draw shapes inside one group shape (ADR 0002).

Every group starts with an invisible frame rectangle spanning the whole layout box. It keeps the
group's bounding box equal to the layout size, so re-rendering at the group's current size is
stable even when labels or bars do not reach the edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import uno
from com.sun.star.awt import Point, Size

from librecharts.core.primitives import Line, Primitive, Rect, Text

PALETTE = (0x8FB4E3, 0x5E8AC7, 0xC9D8EE, 0xA6A6A6, 0xF4B183, 0xD9D9D9)
TEXT_COLOR = 0x000000
LINE_COLOR = 0x404040
LINE_WIDTH = 25  # 1/100 mm
FONT_HEIGHT_PT = 10.0
ARROW_NAME = "Arrow"  # a line end from LibreOffice's standard arrow list
ARROW_WIDTH = 250  # 1/100 mm

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
    for spec in _specs(primitives, x, y, width, height):
        _create(doc, group, spec)
    return group


def rerender(doc: Any, group: Any, primitives: tuple[Primitive, ...]) -> None:
    """Replace the group's children; position, size, name and z-order of the group are kept.

    ``primitives`` must have been laid out for the group's current size.
    """
    old = [group.getByIndex(i) for i in range(group.getCount())]
    position, size = group.Position, group.Size
    # Add first, then remove: an emptied group may be dissolved by LibreOffice.
    for spec in _specs(primitives, position.X, position.Y, size.Width, size.Height):
        _create(doc, group, spec)
    for shape in old:
        group.remove(shape)


SyncResult = Literal["unchanged", "updated", "mismatch"]


def sync_geometry(group: Any, primitives: tuple[Primitive, ...]) -> SyncResult:
    """Move and resize the existing children to ``primitives`` laid out at the group's box.

    Keeps the shapes themselves, so LibreOffice's own undo of a resize can restore them.
    Returns ``"mismatch"`` (and changes nothing) if the children do not correspond one to one.
    """
    position, size = group.Position, group.Size
    specs = _specs(primitives, position.X, position.Y, size.Width, size.Height)
    children = [group.getByIndex(i) for i in range(group.getCount())]
    if len(children) != len(specs) or any(
        child.ShapeType != f"com.sun.star.drawing.{spec.kind}"
        for child, spec in zip(children, specs, strict=True)
    ):
        return "mismatch"
    changed = False
    for child, spec in zip(children, specs, strict=True):
        pos, sz = child.Position, child.Size
        if (
            abs(pos.X - spec.x) > _TOLERANCE
            or abs(pos.Y - spec.y) > _TOLERANCE
            or abs(sz.Width - spec.width) > _TOLERANCE
            or abs(sz.Height - spec.height) > _TOLERANCE
        ):
            child.Position = Point(spec.x, spec.y)
            child.Size = Size(spec.width, spec.height)
            changed = True
        if isinstance(spec.primitive, Text) and child.String != spec.primitive.text:
            child.String = spec.primitive.text
            changed = True
    return "updated" if changed else "unchanged"


_TOLERANCE = 1  # 1/100 mm; LibreOffice rounds scaled geometry


@dataclass(frozen=True, slots=True)
class _Spec:
    kind: str  # Draw shape type without the com.sun.star.drawing prefix
    x: int
    y: int
    width: int
    height: int
    primitive: Primitive | None  # None for the frame


def _spec(kind: str, p: Primitive | None, x: float, y: float, w: float, h: float) -> _Spec:
    return _Spec(kind, round(x), round(y), max(round(w), 0), max(round(h), 0), p)


def _specs(
    primitives: tuple[Primitive, ...], x: int, y: int, width: int, height: int
) -> list[_Spec]:
    specs = [_spec("RectangleShape", None, x, y, width, height)]
    for p in primitives:
        if isinstance(p, Rect):
            specs.append(_spec("RectangleShape", p, x + p.x, y + p.y, p.width, p.height))
        elif isinstance(p, Line):
            specs.append(_spec("LineShape", p, x + p.x1, y + p.y1, p.x2 - p.x1, p.y2 - p.y1))
        else:
            specs.append(_spec("TextShape", p, x + p.x, y + p.y, p.width, p.height))
    return specs


def _create(doc: Any, group: Any, spec: _Spec) -> None:
    shape = doc.createInstance(f"com.sun.star.drawing.{spec.kind}")
    group.add(shape)
    shape.Position = Point(spec.x, spec.y)
    shape.Size = Size(spec.width, spec.height)
    p = spec.primitive
    if p is None:  # the invisible frame
        shape.FillStyle, shape.LineStyle = _FILL_NONE, _LINE_NONE
    elif isinstance(p, Rect):
        shape.FillStyle, shape.FillColor = _FILL_SOLID, PALETTE[p.series % len(PALETTE)]
        shape.LineStyle = _LINE_NONE
    elif isinstance(p, Line):
        shape.LineStyle, shape.LineColor, shape.LineWidth = _LINE_SOLID, LINE_COLOR, LINE_WIDTH
        if p.arrow:  # the line runs top-left to bottom-right, so its end is (x2, y2)
            shape.LineEndName, shape.LineEndWidth = ARROW_NAME, ARROW_WIDTH
    else:
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
