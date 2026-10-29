# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Arranging the selected shapes (geometry: ``core/arrange.py``). Each command is one undo step.

LibreOffice records no undo action for geometry set through the API, so the change registers an
explicit one (``lo/undo.py``). Charts in the selection are resized like any shape; the resize
watcher (``lo/resize.py``) lays them out again, after an undo as well.
"""

from __future__ import annotations

from typing import Any

from com.sun.star.awt import Point, Size

from librecharts.core.arrange import Rect
from librecharts.lo import undo

DEFAULT_GAP = 500  # 1/100 mm


def selected_shapes(controller: Any) -> list[Any]:
    """The selected shapes of the slide; empty unless it is a multiple selection or one shape."""
    selection = controller.getSelection()
    if selection is None:
        return []
    if hasattr(selection, "Position"):  # a single shape, a group included
        return [selection]
    if hasattr(selection, "getCount"):
        return [selection.getByIndex(i) for i in range(selection.getCount())]
    return []


def rect_of(shape: Any) -> Rect:
    return (shape.Position.X, shape.Position.Y, shape.Size.Width, shape.Size.Height)


def apply(doc: Any, shapes: list[Any], wanted: list[Rect]) -> None:
    """Move and resize ``shapes`` to ``wanted`` as one undo step (nothing if nothing changes)."""
    before = [rect_of(shape) for shape in shapes]
    if before == wanted:
        return

    def set_rects(rects: list[Rect]) -> None:
        for shape, (x, y, width, height) in zip(shapes, rects, strict=True):
            shape.Size = Size(width, height)
            shape.Position = Point(x, y)

    set_rects(wanted)
    undo.add_action(
        doc,
        "Arrange LibreCharts shapes",
        undo=lambda: set_rects(before),
        redo=lambda: set_rects(wanted),
    )
