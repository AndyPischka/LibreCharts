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
_FILL_HATCH = uno.Enum("com.sun.star.drawing.FillStyle", "HATCH")
_HATCH_STYLES = {
    "single": uno.Enum("com.sun.star.drawing.HatchStyle", "SINGLE"),
    "double": uno.Enum("com.sun.star.drawing.HatchStyle", "DOUBLE"),
    "triple": uno.Enum("com.sun.star.drawing.HatchStyle", "TRIPLE"),
}
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
    series (ADR 0016, series colours), indexed like ``ChartState.colors``. With ``patterns`` series
    fills are hatched and line series dashed beside their colours (M20, ADR 0030).
    """

    scheme: style.Scheme = style.DEFAULT
    colors: tuple[int | None, ...] = ()
    patterns: bool = False
    size_override: float | None = None  # per-chart font size (M22)

    def color(self, series: int) -> int:
        """The fill colour of a series index."""
        return self.scheme.color(series, self.colors)

    def muted(self, color: int) -> int:
        """``color`` mixed far towards the background: the look of an unfocused element (M22)."""
        return style.mix(color, self.scheme.background, 0.75)

    def muted_text(self) -> int:
        """A readable but quiet text colour for muted free text."""
        return style.mix(self.scheme.text, self.scheme.background, 0.5)

    def text_on(self, fill: int) -> int:
        """A readable text colour on ``fill``."""
        return self.scheme.text_on(fill)

    @property
    def font_size(self) -> float:
        return self.size_override if self.size_override is not None else self.scheme.font_size


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


def describe(group: Any, title: str, description: str) -> None:
    """Give the chart group its alternative text (M20, ADR 0030); unchanged values stay unwritten,
    because every write fires a modify event. ODP keeps it; LibreOffice's PPTX filter drops it, so
    a chart from a PPTX file gets it back with its next redraw."""
    if group.Title != title:
        group.Title = title
    if group.Description != description:
        group.Description = description


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
            if label.key is not None and child.Name != label_name(label.key):
                child.Name = label_name(label.key)
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


def _hatch(pattern: style.Hatch, fill: int) -> Any:
    hatch = uno.createUnoStruct("com.sun.star.drawing.Hatch")
    hatch.Style = _HATCH_STYLES[pattern.style]
    hatch.Color = style.hatch_color(fill)
    hatch.Distance = style.HATCH_DISTANCE
    hatch.Angle = pattern.angle
    return hatch


def _series_dash(pattern: style.Dash) -> Any:
    dash = uno.createUnoStruct("com.sun.star.drawing.LineDash")
    dash.Style = uno.Enum("com.sun.star.drawing.DashStyle", "RECT")
    dash.Dots, dash.DotLen = pattern.dots, pattern.dot_length
    dash.Dashes, dash.DashLen = pattern.dashes, pattern.dash_length
    dash.Distance = pattern.distance
    return dash


def _same_struct(current: Any, wanted: Any, names: tuple[str, ...]) -> bool:
    try:
        return all(getattr(current, name) == getattr(wanted, name) for name in names)
    except Exception:
        return False


_HATCH_FIELDS = ("Style", "Color", "Distance", "Angle")
_DASH_FIELDS = ("Style", "Dots", "DotLen", "Dashes", "DashLen", "Distance")


def _series_fill(ops: _Style, series: int, color: int, look: Look) -> None:
    """A series fill: plain colour, or the colour under a hatch when the chart shows patterns."""
    pattern = style.hatch(series) if look.patterns else None
    ops.set("FillColor", color)
    if pattern is None:
        ops.set("FillStyle", _FILL_SOLID)
        return
    ops.set("FillStyle", _FILL_HATCH)
    ops.set("FillBackground", True)
    ops.set_struct("FillHatch", _hatch(pattern, color), _HATCH_FIELDS)


def _series_line(ops: _Style, series: int, look: Look) -> None:
    """A line series: solid, or dashed by its index when the chart shows patterns."""
    pattern = style.dash(series) if look.patterns else None
    if pattern is None:
        ops.set("LineStyle", _LINE_SOLID)
        return
    ops.set("LineStyle", _LINE_DASH)
    ops.set_struct("LineDash", _series_dash(pattern), _DASH_FIELDS)


def label_name(key: Any) -> str:
    """The name of a label shape: ``librecharts-label:<role>:<category>:<series>`` (M22)."""
    series = "" if key.series is None else str(key.series)
    return f"librecharts-label:{key.role}:{key.category}:{series}"


def _muted_color(look: Look, series: int, muted: bool) -> int:
    """The series colour, mixed towards the background when the element is outside the focus."""
    color = look.color(series)
    return look.muted(color) if muted else color


def _text_color(label: Text, look: Look) -> int:
    if label.fill is not None:
        fill = _muted_color(look, label.fill, label.muted)
        return look.text_on(fill)
    return look.muted_text() if label.muted else look.scheme.text


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

    def set_struct(self, name: str, value: Any, names: tuple[str, ...]) -> None:
        """Add a struct property unless its fields ``names`` already have these values."""
        if self.update and _same_struct(getattr(self.shape, name), value, names):
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
            style.set("LineColor", _muted_color(look, p.series, p.muted))
            style.set("LineWidth", LINE_WIDTH)
        elif isinstance(p, Polygon):
            _series_fill(style, p.series, _muted_color(look, p.series, p.muted), look)
            style.set("LineStyle", _LINE_NONE)
        elif isinstance(p, Polyline) and p.series in (POSITIVE, NEGATIVE):
            style.set("FillStyle", _FILL_NONE)
            style.set("LineStyle", _LINE_SOLID)
            style.set("LineColor", TICK_COLOR if p.series == POSITIVE else CROSS_COLOR)
            style.set("LineWidth", ELEMENT_LINE_WIDTH)
        elif isinstance(p, Polyline):
            style.set("FillStyle", _FILL_NONE)
            _series_line(style, p.series, look)
            style.set("LineColor", _muted_color(look, p.series, p.muted))
            style.set("LineWidth", LINE_WIDTH)
            if p.dashed:
                style.set("LineStyle", _LINE_DASH)
                style.set_struct("LineDash", _dash(), _DASH_FIELDS)
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
            color = _muted_color(look, p.series, p.muted)
        _series_fill(style, p.series, color, look)
        style.set("LineStyle", _LINE_NONE)
    elif isinstance(p, Bubble):
        _series_fill(style, p.series, _muted_color(look, p.series, p.muted), look)
        style.set("LineStyle", _LINE_NONE)
        style.set("FillTransparence", BUBBLE_TRANSPARENCY)
    elif isinstance(p, Marker):
        style.set("FillStyle", _FILL_SOLID)
        style.set("FillColor", _muted_color(look, p.series, p.muted))
        style.set("LineStyle", _LINE_NONE)
        style.set("FillTransparence", 0)
    elif isinstance(p, Line):
        line_style = _LINE_DASH if p.role == "helper" else _LINE_SOLID
        if p.role == "grid":
            color, width = look.scheme.grid(), GRID_WIDTH
        elif p.role == "axis":
            color, width = look.scheme.line, AXIS_WIDTH
        else:
            color, width = look.scheme.line, LINE_WIDTH
        if p.muted:
            color = look.muted(color)
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
        if label.key is not None:
            style.set("Name", label_name(label.key))
        elif label.name:
            style.set("Name", label.name)
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
        style.set("TextRotation", label.rotation * 100)
    style.apply()
