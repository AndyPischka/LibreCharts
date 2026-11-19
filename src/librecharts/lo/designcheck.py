# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Corporate design check: read every slide, apply the fixes as one undo step (ADR 0029).

The rules and the comparison are ``core/designcheck.py``; this module only turns shapes into
``ShapeInfo`` records and writes the fixes back. Charts are read as a whole (their frame is their
box); Harvey balls and check marks keep their fixed colours. Plain groups are entered, their
children are checked for colours and fonts, the group itself for its position.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uno
from com.sun.star.awt import Point, Size

from librecharts.core import designcheck as core
from librecharts.lo import chart, links, render, scheme, store, undo
from librecharts.lo import elements as lo_elements

_FILL_SOLID = uno.Enum("com.sun.star.drawing.FillStyle", "SOLID")
_LINE_NONE = uno.Enum("com.sun.star.drawing.LineStyle", "NONE")
_NO_FILL_CHECK = (  # their look is not a fill or line colour of the presentation
    "com.sun.star.drawing.GraphicObjectShape",
    "com.sun.star.drawing.OLE2Shape",
    "com.sun.star.drawing.MediaShape",
    "com.sun.star.drawing.TableShape",
    "com.sun.star.presentation.GraphicObjectShape",
    "com.sun.star.presentation.OLE2Shape",
    "com.sun.star.presentation.ChartShape",
    "com.sun.star.presentation.TableShape",
)
GROUP = "com.sun.star.drawing.GroupShape"
AUTOMATIC = -1  # CharColor of text in the automatic colour
LABEL_LENGTH = 30  # characters of a shape's text shown as its label


@dataclass(frozen=True, slots=True)
class _Change:
    """One property write, with the value it replaces, so the undo action can take it back."""

    target: Any
    name: str
    old: Any
    new: Any


def inspect(doc: Any, rules: core.Rules) -> core.Result:
    """Check ``doc`` against ``rules``; changes nothing."""
    shapes, _ = collect(doc)
    return core.check(shapes, rules, scheme.load(doc), slide_size(doc))


def check_and_fix(doc: Any, rules: core.Rules, *, undo_action: bool = True) -> core.Result:
    """Check ``doc`` and fix every deviation: one undo step. Returns what was found."""
    shapes, handles = collect(doc)
    result = core.check(shapes, rules, scheme.load(doc), slide_size(doc))
    if not result.clean:
        apply(doc, result, handles, undo_action=undo_action)
    return result


def slide_size(doc: Any) -> tuple[int, int]:
    pages = doc.getDrawPages()
    if not pages.getCount():
        return 0, 0
    page = pages.getByIndex(0)
    return int(page.Width), int(page.Height)


def collect(doc: Any) -> tuple[list[core.ShapeInfo], dict[tuple[int, tuple[int, ...]], Any]]:
    """Every shape of every slide as a ``ShapeInfo``, and the shapes by (slide, path)."""
    shapes: list[core.ShapeInfo] = []
    handles: dict[tuple[int, tuple[int, ...]], Any] = {}
    pages = doc.getDrawPages()
    for slide in range(pages.getCount()):
        page = pages.getByIndex(slide)
        for index in range(page.getCount()):
            _visit(page.getByIndex(index), slide, (index,), shapes, handles, top=True)
    # Master slides and layouts carry their own shapes; negative indices keep them apart.
    masters = doc.getMasterPages()
    for index in range(masters.getCount()):
        page = masters.getByIndex(index)
        for child in range(page.getCount()):
            _visit(page.getByIndex(child), -1 - index, (child,), shapes, handles, top=True)
    return shapes, handles


def _visit(
    shape: Any,
    slide: int,
    path: tuple[int, ...],
    shapes: list[core.ShapeInfo],
    handles: dict[tuple[int, tuple[int, ...]], Any],
    *,
    top: bool,
) -> None:
    handles[(slide, path)] = shape
    label = _label(shape, path)
    if store.chart_id_of(shape) is not None:
        box = render.layout_box(shape) if top else None
        shapes.append(core.ShapeInfo(slide, path, label, "chart", box))
        return
    if lo_elements.element_of(shape) is not None:
        shapes.append(core.ShapeInfo(slide, path, label, "element", _box(shape) if top else None))
        return
    if shape.ShapeType == GROUP:
        if top:
            shapes.append(core.ShapeInfo(slide, path, label, "element", _box(shape)))
        for index in range(shape.getCount()):
            _visit(shape.getByIndex(index), slide, (*path, index), shapes, handles, top=False)
        return
    fonts, colours = _text_style(shape)
    shapes.append(
        core.ShapeInfo(
            slide,
            path,
            label,
            "shape",
            _box(shape) if top else None,
            fill=_fill(shape),
            line=_line(shape),
            fonts=fonts,
            text_colors=colours,
        )
    )


def _label(shape: Any, path: tuple[int, ...]) -> str:
    """How the report names a shape: its name, the start of its text, or its number."""
    with contextlib.suppress(Exception):
        if shape.Name:
            return str(shape.Name)
    with contextlib.suppress(Exception):
        content = " ".join(str(shape.getString()).split())
        if content:
            return content if len(content) <= LABEL_LENGTH else content[:LABEL_LENGTH] + "…"
    return "#" + ".".join(str(index + 1) for index in path)


def _box(shape: Any) -> tuple[int, int, int, int]:
    position, size = shape.Position, shape.Size
    return position.X, position.Y, size.Width, size.Height


def _has(shape: Any, name: str) -> bool:
    try:
        return bool(shape.getPropertySetInfo().hasPropertyByName(name))
    except Exception:
        return False


def _fill(shape: Any) -> int | None:
    if shape.ShapeType in _NO_FILL_CHECK or not _has(shape, "FillStyle"):
        return None
    return int(shape.FillColor) if shape.FillStyle == _FILL_SOLID else None


def _line(shape: Any) -> int | None:
    if shape.ShapeType in _NO_FILL_CHECK or not _has(shape, "LineStyle"):
        return None
    return None if shape.LineStyle == _LINE_NONE else int(shape.LineColor)


def _portions(shape: Any) -> list[Any]:
    """The non-empty text portions of a shape (an empty presentation placeholder has none)."""
    if shape.ShapeType in _NO_FILL_CHECK or not hasattr(shape, "getText"):
        return []
    with contextlib.suppress(Exception):
        if shape.IsEmptyPresentationObject:
            return []
    found: list[Any] = []
    try:
        paragraphs = shape.getText().createEnumeration()
        while paragraphs.hasMoreElements():
            paragraph = paragraphs.nextElement()
            if not hasattr(paragraph, "createEnumeration"):
                continue  # a text table
            portions = paragraph.createEnumeration()
            while portions.hasMoreElements():
                portion = portions.nextElement()
                if str(portion.getString()).strip():
                    found.append(portion)
    except Exception:
        return []
    return found


def _text_style(shape: Any) -> tuple[tuple[str, ...], tuple[int, ...]]:
    fonts: dict[str, None] = {}
    colours: dict[int, None] = {}
    for portion in _portions(shape):
        fonts.setdefault(str(portion.CharFontName), None)
        colour = int(portion.CharColor)
        if colour != AUTOMATIC:
            colours.setdefault(colour, None)
    return tuple(fonts), tuple(colours)


def apply(
    doc: Any,
    result: core.Result,
    handles: dict[tuple[int, tuple[int, ...]], Any],
    *,
    undo_action: bool = True,
) -> None:
    """Write the fixes of ``result`` (and its scheme) into ``doc``: one undo step."""
    previous = scheme.load(doc)
    changes: list[_Change] = []
    moves: list[tuple[Any, tuple[int, int, int, int], tuple[int, int, int, int]]] = []
    with undo.recording_locked(doc):
        for fix in result.fixes:
            shape = handles.get((fix.slide, fix.path))
            if shape is None:
                continue
            changes += _fix_colours_and_fonts(shape, fix)
            if fix.box is not None:
                before = _chart_box(shape)
                _place(doc, shape, fix.box)
                moves.append((shape, before, fix.box))
        for change in changes:
            change.target.setPropertyValue(change.name, change.new)
    if result.scheme is not None:
        chart.apply_scheme(doc, result.scheme)
    if not undo_action:
        return
    new_scheme = result.scheme

    def undo_fix() -> None:
        _replay(doc, changes, moves, back=True)
        if new_scheme is not None:
            chart.apply_scheme(doc, previous)

    def redo_fix() -> None:
        _replay(doc, changes, moves, back=False)
        if new_scheme is not None:
            chart.apply_scheme(doc, new_scheme)

    undo.add_action(doc, "Fix corporate design", undo=undo_fix, redo=redo_fix)


def _replay(
    doc: Any,
    changes: list[_Change],
    moves: list[tuple[Any, tuple[int, int, int, int], tuple[int, int, int, int]]],
    *,
    back: bool,
) -> None:
    with undo.recording_locked(doc):
        for change in reversed(changes) if back else changes:
            with contextlib.suppress(Exception):  # a shape deleted since
                change.target.setPropertyValue(change.name, change.old if back else change.new)
        for shape, before, after in reversed(moves) if back else moves:
            with contextlib.suppress(Exception):
                _place(doc, shape, before if back else after)


def _fix_colours_and_fonts(shape: Any, fix: core.Fix) -> list[_Change]:
    changes: list[_Change] = []
    if fix.colors:
        for name, current in (("FillColor", _fill(shape)), ("LineColor", _line(shape))):
            if current is not None and current in fix.colors:
                changes.append(_Change(shape, name, current, fix.colors[current]))
    if not (fix.colors or fix.fonts):
        return changes
    text = shape.getText() if hasattr(shape, "getText") else None
    for portion in _portions(shape):
        font, colour = str(portion.CharFontName), int(portion.CharColor)
        writes: list[tuple[str, Any, Any]] = []
        if font in fix.fonts:
            writes.append(("CharFontName", font, fix.fonts[font]))
        if colour in fix.colors:
            writes.append(("CharColor", colour, fix.colors[colour]))
        if not writes:
            continue
        # Character attributes set on a portion object lose against the paragraph's: use a cursor.
        cursor = text.createTextCursorByRange(portion) if text is not None else portion
        changes += [_Change(cursor, name, old, new) for name, old, new in writes]
    return changes


def _chart_box(shape: Any) -> tuple[int, int, int, int]:
    """The box the check saw: a chart's frame, any other shape's own position and size."""
    return render.layout_box(shape) if store.chart_id_of(shape) is not None else _box(shape)


def _place(doc: Any, shape: Any, box: tuple[int, int, int, int]) -> None:
    """Move (and resize) ``shape`` to ``box``; a chart by its frame, then laid out again."""
    x, y, width, height = box
    if store.chart_id_of(shape) is None:
        shape.Position = Point(x, y)
        shape.Size = Size(width, height)
        return
    frame_x, frame_y, frame_w, frame_h = render.layout_box(shape)
    if (frame_w, frame_h) != (width, height) and frame_w and frame_h:
        # The group scales its children; a label moved out of the chart scales with them.
        size = shape.Size
        shape.Size = Size(
            round(size.Width * width / frame_w), round(size.Height * height / frame_h)
        )
        frame_x, frame_y, _, _ = render.layout_box(shape)
    position = shape.Position
    shape.Position = Point(position.X + x - frame_x, position.Y + y - frame_y)
    if (frame_w, frame_h) != (width, height):
        chart.fit_to_size(doc, shape)


def read_rules(location: str) -> core.Rules:
    """The corporate design file at ``location`` (a URL or system path)."""
    try:
        path = uno.fileUrlToSystemPath(links.as_url(location))
        content = Path(path).read_text(encoding="utf-8-sig")
    except Exception as exc:  # not a file URL, missing, unreadable
        raise core.DesignError(str(exc)) from exc
    return core.rules_from_json(content)
