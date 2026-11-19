# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Process, chevron, pyramid and icon graphics in a presentation (M26)."""

from __future__ import annotations

from typing import Any

from librecharts.core import graphics
from librecharts.lo import render, undo

DEFAULT_SHARE = 0.7


def labels(group: Any) -> tuple[str, ...]:
    """The text of the child text shapes in reading order."""
    found: list[str] = []
    for index in range(group.getCount()):
        child = group.getByIndex(index)
        if child.ShapeType == "com.sun.star.drawing.TextShape":
            found.append(str(child.String))
    return tuple(found)


def insert(doc: Any, page: Any, graphic: graphics.Graphic, labels: tuple[str, ...] = ()) -> Any:
    """Insert ``graphic`` centred on ``page`` as one undo step."""
    width = round(page.Width * DEFAULT_SHARE)
    height = round(page.Height * (0.2 if graphic.kind != "icon" else 0.12))
    x, y = (page.Width - width) // 2, (page.Height - height) // 2
    primitives = graphics.layout(graphic, width, height, labels)
    with undo.recording_locked(doc):
        group = render.render_group(doc, page, primitives, x, y, width, height)
        group.Name = graphics.name(graphic)
        title = _alt(graphic)
        render.describe(group, title, title)
    undo.add_action(
        doc,
        "Insert LibreCharts graphic",
        undo=lambda: page.remove(group),
        redo=lambda: page.add(group),
    )
    return group


def find(group: Any) -> graphics.Graphic | None:
    try:
        return graphics.parse(str(group.Name))
    except AttributeError:
        return None


def _alt(graphic: graphics.Graphic) -> str:
    from librecharts.core.messages import text

    return text("alt_graphic", "en", kind=graphic.kind, name=graphic.icon or str(graphic.steps))


def all_graphics(doc: Any) -> list[Any]:
    """Every graphic group on every slide."""
    found: list[Any] = []
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for child in range(page.getCount()):
            shape = page.getByIndex(child)
            if find(shape) is not None:
                found.append(shape)
    return found


def change(doc: Any, group: Any, graphic: graphics.Graphic) -> None:
    """Replace the graphic's variant, keeping the labels where possible."""
    previous = find(group)
    if previous is None:
        raise ValueError("shape is not a LibreCharts graphic")
    _, _, width, height = render.layout_box(group)

    def apply(item: graphics.Graphic) -> None:
        texts = labels(group) if item.kind != "icon" else ()
        render.rerender(doc, group, graphics.layout(item, width, height, texts))
        group.Name = graphics.name(item)
        title = _alt(item)
        render.describe(group, title, title)

    apply(graphic)
    undo.add_action(
        doc,
        "Change LibreCharts graphic",
        undo=lambda: apply(previous),
        redo=lambda: apply(graphic),
    )


def fit_to_size(doc: Any, group: Any) -> bool:
    """Re-lay out a graphic at its current size; ``True`` if anything moved."""
    graphic = find(group)
    if graphic is None:
        return False
    try:
        _, _, width, height = render.layout_box(group)
        primitives = graphics.layout(graphic, width, height, labels(group))
        return render.sync_geometry(group, primitives) == "updated"
    except ValueError:
        return False
