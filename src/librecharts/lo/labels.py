# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Label placement in LibreOffice: find labels the user dragged and keep them as offsets (ADR 0023).

The user drags value labels and totals inside the entered chart group. The resize watcher calls
:func:`check` for the charts a label can have moved in; ``core.labels.moved`` compares the shapes
with the layout for the chart's state and returns the new offsets. They are stored without an
undo action (LibreOffice records the drag itself, and its undo moves the label back, which the next
check turns into an offset again) and the moved labels are synced in place.

:func:`start` is the *Move labels* command: it enters the chart group and shows an info bar until
the user leaves it.
"""

from __future__ import annotations

import contextlib
import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XCallback, XKeyHandler
from com.sun.star.view import XSelectionChangeListener

from librecharts.core import labels
from librecharts.core.layout.chart import layout_chart
from librecharts.core.messages import text
from librecharts.core.state_io import StateError
from librecharts.lo import render, samescale, scheme, store, ui

INFOBAR = "org.librecharts.labels"
_INFOBAR_INFO = 1  # com.sun.star.frame.InfobarType.INFO
_ESCAPE = 1281  # com.sun.star.awt.Key.ESCAPE
_POLY_SHAPES = ("com.sun.star.drawing.PolyLineShape", "com.sun.star.drawing.PolyPolygonShape")

_sessions: dict[str, _Session] = {}


def read_boxes(group: Any) -> list[labels.Box]:
    """The box of every child except the frame, relative to the layout box, in one pass.

    (A proxy kept in a list and read later intermittently returned default geometry on
    LibreOffice 26.8: read each child as soon as it is fetched.)
    """
    x, y, _, _ = render.layout_box(group)
    boxes: list[labels.Box] = []
    for index in range(1, group.getCount()):
        child = group.getByIndex(index)
        if child.ShapeType in _POLY_SHAPES:  # the points carry the geometry, not Position/Size
            points = [(p.X, p.Y) for outer in child.PolyPolygon for p in outer]
            left, top = min(px for px, _ in points), min(py for _, py in points)
            right, bottom = max(px for px, _ in points), max(py for _, py in points)
            boxes.append((left - x, top - y, right - left, bottom - top))
            continue
        position, size = child.Position, child.Size
        boxes.append((position.X - x, position.Y - y, size.Width, size.Height))
    return boxes


def check(doc: Any, group: Any) -> bool:
    """Store the labels the user moved in the chart of ``group``; ``True`` if offsets changed.

    Anything else that differs from the layout (a series name, an axis label or a bar dragged by
    hand) is put back at once: the chart always matches its layout. Charts without readable state
    are left alone.
    """
    chart_id = store.resolve(doc, group)
    if chart_id is None:
        return False
    try:
        state = store.read_state(doc, chart_id)
        if state is None:
            return False
        _, _, width, height = render.layout_box(group)
        length = samescale.group_length_per_unit(doc, chart_id, state)
        primitives = layout_chart(state, width, height, length)
        found = labels.moved(primitives, read_boxes(group), state.labels)
        look = scheme.look(doc, state)
        if found is None:
            render.sync_geometry(group, primitives, look)
            return False
        if found == state.labels:
            return False
        moved = replace(state, labels=found)
        store.write_state(doc, chart_id, moved)
        render.sync_geometry(group, layout_chart(moved, width, height, length), look)
    except (StateError, ValueError):  # corrupt state, or the box is too small to lay out
        return False
    return True


def start(ctx: Any, frame: Any, group: Any) -> None:
    """Enter the chart in ``group`` so that its labels can be dragged; an info bar says how."""
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _sessions:
        _sessions[key].finish()
    _sessions[key] = _Session(key, ctx, frame, group)


def active(doc: Any) -> bool:
    """Whether a *Move labels* session is running in ``doc`` (for tests)."""
    return str(doc.RuntimeUID) in _sessions


class _Session(unohelper.Base, XSelectionChangeListener, XKeyHandler, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any, group: Any) -> None:
        self.key, self.ctx, self.frame, self.group = key, ctx, frame, group
        self.controller = frame.getController()
        self.chart_id = store.chart_id_of(group)
        self._done = False
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        self.controller.select(group)
        ui.uno_command(ctx, frame, ".uno:EnterGroup")  # before listening: entering deselects
        self.controller.addSelectionChangeListener(self)
        self.controller.addKeyHandler(self)
        self._show_hint(text("move_labels_hint", ui.ui_locale(ctx)))

    def finish(self) -> None:
        """End the session; leaving the group happens outside the current notification."""
        if self._done:
            return
        self._done = True
        self._async.addCallback(self, None)  # None: void any, see lo/resize.py

    # XSelectionChangeListener
    def selectionChanged(self, event: Any) -> None:
        try:
            if self._done:
                return
            selection = self.controller.getSelection()
            if selection is None or not hasattr(selection, "getCount"):
                return
            if selection.getCount() and not self._in_chart(selection.getByIndex(0)):
                self.finish()  # the user selected something outside the chart
        except Exception:
            # Never let an exception escape into LibreOffice's notification loop.
            traceback.print_exc()

    # XKeyHandler
    def keyPressed(self, event: Any) -> bool:
        if event.KeyCode != _ESCAPE:
            return False
        try:
            self.finish()
        except Exception:
            traceback.print_exc()
        return True

    def keyReleased(self, event: Any) -> bool:
        return False

    def disposing(self, event: Any) -> None:
        self._done = True
        _sessions.pop(self.key, None)

    # XCallback
    def notify(self, data: Any) -> None:
        try:
            _sessions.pop(self.key, None)
            with contextlib.suppress(Exception):  # the presentation may be gone already
                self.controller.removeSelectionChangeListener(self)
                self.controller.removeKeyHandler(self)
            with contextlib.suppress(Exception):
                if self.controller.hasInfobar(INFOBAR):
                    self.controller.removeInfobar(INFOBAR)
            ui.uno_command(self.ctx, self.frame, ".uno:LeaveGroup")
            self.controller.select(self.group)
        except Exception:
            traceback.print_exc()

    def _in_chart(self, shape: Any) -> bool:
        try:
            return store.chart_id_of(shape.getParent()) == self.chart_id
        except AttributeError:  # not a shape inside a group
            return False

    def _show_hint(self, message: str) -> None:
        try:
            self.controller.appendInfobar(INFOBAR, "LibreCharts", message, _INFOBAR_INFO, (), False)
        except Exception:  # no info bar (e.g. a hidden document): dragging works without it
            traceback.print_exc()
