# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Turn layout primitives into native Draw shapes inside one group shape (ADR 0002).

Every group starts with an invisible frame rectangle spanning the whole layout box. It keeps the
group's bounding box equal to the layout size, so re-rendering at the group's current size is
stable even when labels or bars do not reach the edges. A label the user moved out of the chart
makes the group's bounding box grow; the frame stays the layout box (:func:`layout_box`), so
position and size of a chart are always read from it, never from the group (ADR 0023).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

import uno
from com.sun.star.awt import Point, Size

from librecharts.core import style
from librecharts.core.primitives import (
    BACKGROUND,
    MARKER_SIZE,
    NEGATIVE,
    POSITIVE,
    SHADE,
    Bubble,
    Line,
    Marker,
    Polygon,
    Polyline,
    Primitive,
    Rect,
    Text,
)

LINE_WIDTH = 25  # 1/100 mm
AXIS_WIDTH = 20  # 1/100 mm
GRID_WIDTH = 15  # 1/100 mm
ARROW_NAME = "Arrow"  # a line end from LibreOffice's standard arrow list
ARROW_WIDTH = 250  # 1/100 mm
DASH_LENGTH = 100  # 1/100 mm, dashes and gaps of helper lines
BUBBLE_TRANSPARENCY = 30  # percent; overlapping bubbles stay visible
ELEMENT_LINE_WIDTH = 60  # 1/100 mm, tick and cross of check marks
TICK_COLOR = 0x2E7D32
CROSS_COLOR = 0xC62828
BOLD = 150.0  # com.sun.star.awt.FontWeight.BOLD
NORMAL = 100.0  # com.sun.star.awt.FontWeight.NORMAL

_FILL_NONE = uno.Enum("com.sun.star.drawing.FillStyle", "NONE")
_FILL_SOLID = uno.Enum("com.sun.star.drawing.FillStyle", "SOLID")
_LINE_NONE = uno.Enum("com.sun.star.drawing.LineStyle", "NONE")
_LINE_SOLID = uno.Enum("com.sun.star.drawing.LineStyle", "SOLID")
_LINE_DASH = uno.Enum("com.sun.star.drawing.LineStyle", "DASH")
_V_CENTER = uno.Enum("com.sun.star.drawing.TextVerticalAdjust", "CENTER")
_H_BLOCK = uno.Enum("com.sun.star.drawing.TextHorizontalAdjust", "BLOCK")
_PARA_ADJUST = {
    "left": uno.Enum("com.sun.star.style.ParagraphAdjust", "LEFT"),
    "center": uno.Enum("com.sun.star.style.ParagraphAdjust", "CENTER"),
    "right": uno.Enum("com.sun.star.style.ParagraphAdjust", "RIGHT"),
}


@dataclass(frozen=True, slots=True)
class Look:
    """How the shapes of a chart are coloured and lettered (ADR 0016).

    ``scheme`` is the document-wide colour scheme; ``colors`` holds the palette indices of single
    series (ADR 0016, series colours), indexed like ``ChartState.colors``.
    """

    scheme: style.Scheme = style.DEFAULT
    colors: tuple[int | None, ...] = ()

    def color(self, series: int) -> int:
        """The fill colour of a series index."""
        return self.scheme.color(series, self.colors)

    def text_on(self, fill: int) -> int:
        """A readable text colour on ``fill``."""
        return self.scheme.text_on(fill)

    @property
    def font_size(self) -> float:
        return self.scheme.font_size


DEFAULT_LOOK = Look()


def render_group(
    doc: Any,
    page: Any,
    primitives: tuple[Primitive, ...],
    x: int,
    y: int,
    width: int,
    height: int,
    look: Look = DEFAULT_LOOK,
) -> Any:
    """Create a new group at (``x``, ``y``) on ``page`` holding the frame and ``primitives``."""
    group = doc.createInstance("com.sun.star.drawing.GroupShape")
    page.add(group)
    for spec in _specs(primitives, x, y, width, height):
        _create(doc, group, spec, look)
    return group


def layout_box(group: Any) -> tuple[int, int, int, int]:
    """The chart's layout box (x, y, width, height): the position and size of its invisible frame.

    The group's own bounding box is the same unless a label was moved out of the chart.
    """
    frame = group.getByIndex(0) if group.getCount() else group
    position, size = frame.Position, frame.Size
    return position.X, position.Y, size.Width, size.Height


def rerender(
    doc: Any, group: Any, primitives: tuple[Primitive, ...], look: Look = DEFAULT_LOOK
) -> None:
    """Draw ``primitives`` in the group; position, size, name and z-order of the group are kept.

    ``primitives`` must have been laid out for the chart's current layout box. If their structure
    (kinds and order) is the one already drawn, the existing shapes are updated in place: the undo
    steps LibreOffice recorded for them (a resize, a label drag) keep working. Only a changed
    structure replaces the children.
    """
    x, y, width, height = layout_box(group)
    specs = _specs(primitives, x, y, width, height)
    old = [group.getByIndex(i) for i in range(group.getCount())]
    if _same_structure(old, specs):
        for shape, spec in zip(old[1:], specs[1:], strict=True):  # the frame stays as it is
            _style(shape, spec, look, update=True)
        return
    # Add first, then remove: an emptied group may be dissolved by LibreOffice.
    for spec in specs:
        _create(doc, group, spec, look)
    for shape in old:
        group.remove(shape)


def _same_structure(children: list[Any], specs: list[_Spec]) -> bool:
    """Whether the children correspond one to one to ``specs``: the same shape kinds, and lines
    with the arrow they need (the one thing the renderer cannot take back from a shape)."""
    return len(children) == len(specs) and all(
        child.ShapeType == f"com.sun.star.drawing.{spec.kind}" and _arrow_fits(child, spec)
        for child, spec in zip(children, specs, strict=True)
    )


def _arrow_fits(child: Any, spec: _Spec) -> bool:
    p = spec.primitive
    if not isinstance(p, Line):
        return True
    start, end = (ARROW_NAME, "") if _drawn_reversed(p) else ("", ARROW_NAME)
    if not p.arrow:
        start = end = ""
    return child.LineStartName == start and child.LineEndName == end


def _drawn_reversed(p: Line) -> bool:
    """Whether a line runs against the direction of its bounding box: (x2, y2) is its start."""
    return p.arrow and (p.x2 < p.x1 or p.y2 < p.y1)


SyncResult = Literal["unchanged", "updated", "mismatch"]


def sync_geometry(
    group: Any, primitives: tuple[Primitive, ...], look: Look | None = None
) -> SyncResult:
    """Move and resize the existing children to ``primitives`` laid out at the chart's layout box.

    Keeps the shapes themselves, so LibreOffice's own undo of a resize can restore them. With a
    ``look`` the text colour of labels is synced too (a label moved off its segment). Returns
    ``"mismatch"`` (and changes nothing) if the children do not correspond one to one.
    """
    x, y, width, height = layout_box(group)
    specs = _specs(primitives, x, y, width, height)
    children = [group.getByIndex(i) for i in range(group.getCount())]
    if len(children) != len(specs) or any(
        child.ShapeType != f"com.sun.star.drawing.{spec.kind}"
        for child, spec in zip(children, specs, strict=True)
    ):
        return "mismatch"
    changed = False
    for child, spec in zip(children, specs, strict=True):
        if spec.points is not None:  # a poly shape: its points carry the geometry
            if not _same_points(child.PolyPolygon, spec.points):
                child.PolyPolygon = spec.points
                changed = True
            continue
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
        if isinstance(spec.primitive, Text):
            label = spec.primitive
            if child.String != label.shown:
                child.String = label.shown
                changed = True
            if look is not None and child.CharColor != _text_color(label, look):
                child.CharColor = _text_color(label, look)
                changed = True
    return "updated" if changed else "unchanged"


def _same_points(current: Any, wanted: tuple[tuple[Point, ...], ...]) -> bool:
    """Whether the shape's polygon already has ``wanted`` (within rounding)."""
    current = tuple(current)
    if len(current) != len(wanted) or any(
        len(outer) != len(inner) for outer, inner in zip(current, wanted, strict=True)
    ):
        return False
    return all(
        abs(point.X - target.X) <= _TOLERANCE and abs(point.Y - target.Y) <= _TOLERANCE
        for outer, inner in zip(current, wanted, strict=True)
        for point, target in zip(outer, inner, strict=True)
    )


_TOLERANCE = 1  # 1/100 mm; LibreOffice rounds scaled geometry


@dataclass(frozen=True, slots=True)
class _Spec:
    kind: str  # Draw shape type without the com.sun.star.drawing prefix
    x: int
    y: int
    width: int
    height: int
    primitive: Primitive | None  # None for the frame
    points: tuple[tuple[Point, ...], ...] | None = None  # poly shapes: absolute page points


def _spec(
    kind: str,
    p: Primitive | None,
    x: float,
    y: float,
    w: float,
    h: float,
    points: tuple[tuple[Point, ...], ...] | None = None,
) -> _Spec:
    return _Spec(kind, round(x), round(y), max(round(w), 0), max(round(h), 0), p, points)


def _specs(
    primitives: tuple[Primitive, ...], x: int, y: int, width: int, height: int
) -> list[_Spec]:
    specs = [_spec("RectangleShape", None, x, y, width, height)]
    for p in primitives:
        if isinstance(p, Rect):
            specs.append(_spec("RectangleShape", p, x + p.x, y + p.y, p.width, p.height))
        elif isinstance(p, Line):  # by bounding box, see Line
            left, top = x + min(p.x1, p.x2), y + min(p.y1, p.y2)
            specs.append(_spec("LineShape", p, left, top, abs(p.x2 - p.x1), abs(p.y2 - p.y1)))
        elif isinstance(p, (Polyline, Polygon)):
            left = min(px for px, _ in p.points)
            top = min(py for _, py in p.points)
            right = max(px for px, _ in p.points)
            bottom = max(py for _, py in p.points)
            points = (tuple(Point(round(x + px), round(y + py)) for px, py in p.points),)
            kind = "PolyLineShape" if isinstance(p, Polyline) else "PolyPolygonShape"
            specs.append(_spec(kind, p, x + left, y + top, right - left, bottom - top, points))
        elif isinstance(p, Marker):
            specs.append(
                _spec(
                    "EllipseShape",
                    p,
                    x + p.x - MARKER_SIZE / 2,
                    y + p.y - MARKER_SIZE / 2,
                    MARKER_SIZE,
                    MARKER_SIZE,
                )
            )
        elif isinstance(p, Bubble):
            specs.append(
                _spec(
                    "EllipseShape",
                    p,
                    x + p.x - p.diameter / 2,
                    y + p.y - p.diameter / 2,
                    p.diameter,
                    p.diameter,
                )
            )
        else:
            specs.append(_spec("TextShape", p, x + p.x, y + p.y, p.width, p.height))
    return specs


def _dash() -> Any:
    dash = uno.createUnoStruct("com.sun.star.drawing.LineDash")
    dash.Style = uno.Enum("com.sun.star.drawing.DashStyle", "RECT")
    dash.Dashes, dash.DashLen, dash.Distance = 1, DASH_LENGTH, DASH_LENGTH
    return dash


def _text_color(label: Text, look: Look) -> int:
    return look.text_on(look.color(label.fill)) if label.fill is not None else look.scheme.text


def _create(doc: Any, group: Any, spec: _Spec, look: Look) -> None:
    shape = doc.createInstance(f"com.sun.star.drawing.{spec.kind}")
    group.add(shape)
    _style(shape, spec, look)


class _Style:
    """Collects the operations for one shape and applies them in order.

    Consecutive property writes become one ``setPropertyValues`` call, which is much cheaper
    than one write per property; with ``update`` unchanged properties are left out entirely.
    Geometry and text are methods on a drawing shape, not properties, so they stay separate
    operations. Every write fires a document modify event.
    """

    __slots__ = ("ops", "shape", "update")

    def __init__(self, shape: Any, update: bool) -> None:
        self.shape = shape
        self.update = update
        self.ops: list[tuple[str, Any]] = []

    def set(self, name: str, value: Any) -> None:
        """Add a property unless it already has ``value``."""
        if self.update and getattr(self.shape, name) == value:
            return
        self.put(name, value)

    def set_float(self, name: str, value: float) -> None:
        """Add a float property unless it already has ``value`` within rounding."""
        if self.update and abs(float(getattr(self.shape, name)) - value) <= 0.01:
            return
        self.put(name, value)

    def put(self, name: str, value: Any) -> None:
        if self.ops and self.ops[-1][0] == "props":
            names, values = self.ops[-1][1]
            names.append(name)
            values.append(value)
        else:
            self.ops.append(("props", ([name], [value])))

    def geometry(self, spec: _Spec) -> None:
        """Move and resize the shape unless it already has that geometry."""
        if self.update:
            position, size = self.shape.Position, self.shape.Size
            if (
                abs(position.X - spec.x) <= _TOLERANCE
                and abs(position.Y - spec.y) <= _TOLERANCE
                and abs(size.Width - spec.width) <= _TOLERANCE
                and abs(size.Height - spec.height) <= _TOLERANCE
            ):
                return
        self.ops.append(("geometry", (Point(spec.x, spec.y), Size(spec.width, spec.height))))

    def polygon(self, points: tuple[tuple[Point, ...], ...]) -> None:
        self.ops.append(("polygon", points))

    def text(self, value: str) -> None:
        self.ops.append(("text", value))

    def apply(self) -> None:
        for kind, payload in self.ops:
            if kind == "props":
                names, values = payload
                self.shape.setPropertyValues(tuple(names), tuple(values))
            elif kind == "geometry":
                position, size = payload
                self.shape.Position = position
                self.shape.Size = size
            elif kind == "polygon":
                self.shape.PolyPolygon = payload
            elif kind == "text":
                self.shape.String = payload
            else:
                raise ValueError(f"unknown style operation: {kind}")


def _style(shape: Any, spec: _Spec, look: Look, *, update: bool = False) -> None:
    """Set geometry, text and every property the renderer sets: for new and existing shapes.

    With ``update`` (a redraw onto the same shapes) a property is only written when it differs.
    Every write fires a document modify event and costs milliseconds, so a redraw that changes
    little stays fast.
    """
    style = _Style(shape, update)
    p = spec.primitive
    if spec.points is not None:  # polyline or polygon: its points define the geometry
        if not update or not _same_points(shape.PolyPolygon, spec.points):
            style.polygon(spec.points)
        if isinstance(p, Polygon) and p.outline:
            style.set("FillStyle", _FILL_SOLID)
            style.set("FillColor", look.scheme.background)
            style.set("LineStyle", _LINE_SOLID)
            style.set("LineColor", look.color(p.series))
            style.set("LineWidth", LINE_WIDTH)
        elif isinstance(p, Polygon):
            style.set("FillStyle", _FILL_SOLID)
            style.set("FillColor", look.color(p.series))
            style.set("LineStyle", _LINE_NONE)
        elif isinstance(p, Polyline) and p.series in (POSITIVE, NEGATIVE):
            style.set("FillStyle", _FILL_NONE)
            style.set("LineStyle", _LINE_SOLID)
            style.set("LineColor", TICK_COLOR if p.series == POSITIVE else CROSS_COLOR)
            style.set("LineWidth", ELEMENT_LINE_WIDTH)
        elif isinstance(p, Polyline):
            style.set("FillStyle", _FILL_NONE)
            style.set("LineStyle", _LINE_SOLID)
            style.set("LineColor", look.color(p.series))
            style.set("LineWidth", LINE_WIDTH)
        style.apply()
        return
    style.geometry(spec)
    if p is None:  # the invisible frame
        style.set("FillStyle", _FILL_NONE)
        style.set("LineStyle", _LINE_NONE)
    elif isinstance(p, Rect):
        if p.series == BACKGROUND:
            color = look.scheme.background
        elif p.series == SHADE:
            color = look.scheme.shade()
        else:
            color = look.color(p.series)
        style.set("FillStyle", _FILL_SOLID)
        style.set("FillColor", color)
        style.set("LineStyle", _LINE_NONE)
    elif isinstance(p, (Marker, Bubble)):
        style.set("FillStyle", _FILL_SOLID)
        style.set("FillColor", look.color(p.series))
        style.set("LineStyle", _LINE_NONE)
        style.set("FillTransparence", BUBBLE_TRANSPARENCY if isinstance(p, Bubble) else 0)
    elif isinstance(p, Line):
        line_style = _LINE_DASH if p.role == "helper" else _LINE_SOLID
        if p.role == "grid":
            color, width = look.scheme.grid(), GRID_WIDTH
        elif p.role == "axis":
            color, width = look.scheme.line, AXIS_WIDTH
        else:
            color, width = look.scheme.line, LINE_WIDTH
        style.set("LineStyle", line_style)
        style.set("LineColor", color)
        style.set("LineWidth", width)
        if p.role == "helper":
            style.put("LineDash", _dash())
        if _drawn_reversed(p):
            style.set("LineStartName", ARROW_NAME)
            style.set("LineStartWidth", ARROW_WIDTH)
        elif p.arrow:
            style.set("LineEndName", ARROW_NAME)
            style.set("LineEndWidth", ARROW_WIDTH)
    else:
        label = cast("Text", p)  # poly shapes return above; what is left is a label
        style.set("TextAutoGrowHeight", False)
        style.set("TextAutoGrowWidth", False)
        style.set("TextVerticalAdjust", _V_CENTER)
        style.set("TextHorizontalAdjust", _H_BLOCK)
        style.set("TextLeftDistance", 0)
        style.set("TextRightDistance", 0)
        style.set("TextUpperDistance", 0)
        style.set("TextLowerDistance", 0)
        # Text and character properties only stick once the shape is in a group or on a page.
        style.text(label.shown)
        style.set("CharFontName", look.scheme.font_name)
        style.set_float(
            "CharHeight",
            max(look.font_size * 0.8, 4.0) if label.role == "axis" else look.font_size,
        )
        style.set("CharColor", _text_color(label, look))
        style.set("ParaAdjust", _PARA_ADJUST[label.align])
        style.set_float("CharWeight", BOLD if label.role == "heading" else NORMAL)
    style.apply()
