# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Pick mode: the user clicks the columns an annotation connects (M4 plan, spike results).

Mapping mouse pixels to slide coordinates proved unreliable, so LibreOffice hit-tests for us:
pick mode enters the chart group, a click there selects the shape under the mouse, and a
selection listener hands that shape's centre to ``core.picking``. Selecting anything outside the
chart, or ``Esc``, cancels. An info bar says what to click. One session per presentation.

Leaving the group and adding the annotation happen asynchronously, outside the selection
notification that LibreOffice is still processing.
"""

from __future__ import annotations

import contextlib
import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XCallback, XKeyHandler
from com.sun.star.view import XSelectionChangeListener

from librecharts.core.layout.chart import layout_chart
from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState
from librecharts.core.picking import PickSession, placed, target_at
from librecharts.core.primitives import Text
from librecharts.lo import chart, render, store, textdialog, ui

INFOBAR = "org.librecharts.pick"
_INFOBAR_INFO = 1  # com.sun.star.frame.InfobarType.INFO
_ESCAPE = 1281  # com.sun.star.awt.Key.ESCAPE
_TOLERANCE = 2  # 1/100 mm, to recognise the invisible frame by its geometry

_sessions: dict[str, _Pick] = {}


def start(ctx: Any, frame: Any, group: Any, state: ChartState, session: PickSession) -> None:
    """Let the user pick columns of the chart in ``group`` for ``session``'s annotation."""
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _sessions:
        _sessions[key].finish(None)
    _sessions[key] = _Pick(key, ctx, frame, group, state, session)


def active(doc: Any) -> bool:
    """Whether a pick session is running in ``doc`` (for tests and commands)."""
    return str(doc.RuntimeUID) in _sessions


class _Pick(unohelper.Base, XSelectionChangeListener, XKeyHandler, XCallback):
    def __init__(
        self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState, session: PickSession
    ) -> None:
        self.key, self.ctx, self.frame, self.group = key, ctx, frame, group
        self.state, self.session = state, session
        self.controller = frame.getController()
        self.chart_id = store.chart_id_of(group)
        self.locale = ui.ui_locale(ctx)
        self._done = False
        self._result: Annotation | None = None
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        self.controller.select(group)
        ui.uno_command(ctx, frame, ".uno:EnterGroup")  # before listening: entering deselects
        self.controller.addSelectionChangeListener(self)
        self.controller.addKeyHandler(self)
        self._show_prompt()

    def finish(self, annotation: Annotation | None) -> None:
        """End the session, adding ``annotation`` unless it is ``None`` (cancelled)."""
        if self._done:
            return
        self._done, self._result = True, annotation
        self._async.addCallback(self, None)  # None: void any, see lo/resize.py

    # XSelectionChangeListener
    def selectionChanged(self, event: Any) -> None:
        try:
            if self._done:
                return
            shape = _single(self.controller.getSelection())
            if shape is None:  # nothing selected: a click between the columns
                return
            if not self._in_chart(shape):
                self.finish(None)
                return
            position, size = shape.Position, shape.Size
            if self._is_frame(position, size):
                return
            x, y, width, height = render.layout_box(self.group)
            target = target_at(
                self.state,
                width,
                height,
                *self._anchor(
                    shape, position.X - x + size.Width / 2, position.Y - y + size.Height / 2
                ),
            )
            if target is None:
                return
            annotation = self.session.add(target)
            if annotation is None:
                self._show_prompt()
            else:
                self.finish(annotation)
        except Exception:
            # Never let an exception escape into LibreOffice's notification loop.
            traceback.print_exc()

    # XKeyHandler
    def keyPressed(self, event: Any) -> bool:
        if event.KeyCode != _ESCAPE:
            return False
        try:
            self.finish(None)
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
            if self._result is not None:
                annotation = placed(self.state, self._result)
                if annotation.kind == "group_bracket" and not annotation.text:
                    # A group bracket is labelled by the dialog that follows the picks; cancelling
                    # it leaves the chart unchanged.
                    label = textdialog.ask(self.ctx, self.frame, "")
                    if label is not None:
                        chart.add_annotation(
                            self.controller.getModel(),
                            self.group,
                            replace(annotation, text=label),
                        )
                else:
                    chart.add_annotation(self.controller.getModel(), self.group, annotation)
            self.controller.select(self.group)
        except Exception:
            traceback.print_exc()

    def _in_chart(self, shape: Any) -> bool:
        try:
            return store.chart_id_of(shape.getParent()) == self.chart_id
        except AttributeError:  # not a shape inside a group
            return False

    def _is_frame(self, position: Any, size: Any) -> bool:
        x, y, width, height = render.layout_box(self.group)
        return all(
            abs(a - b) <= _TOLERANCE
            for a, b in (
                (position.X, x),
                (position.Y, y),
                (size.Width, width),
                (size.Height, height),
            )
        )

    def _anchor(self, shape: Any, x: float, y: float) -> tuple[float, float]:
        """Where ``shape`` belongs in the chart: its own centre (``x``, ``y``), or for a label the
        user moved the place the layout gives it, so a click on it picks its own column."""
        if not self.state.labels:
            return x, y
        children = [self.group.getByIndex(i) for i in range(self.group.getCount())]
        index = next((i for i, child in enumerate(children) if child == shape), 0)
        if index < 1:  # not found, or the frame
            return x, y
        _, _, width, height = render.layout_box(self.group)
        primitives = layout_chart(replace(self.state, labels=()), width, height)
        if index > len(primitives):
            return x, y
        label = primitives[index - 1]
        if not isinstance(label, Text) or label.key is None:
            return x, y
        return label.x + label.width / 2, label.y + label.height / 2

    def _show_prompt(self) -> None:
        message = text(self.session.prompt, self.locale)
        try:
            if self.controller.hasInfobar(INFOBAR):
                self.controller.updateInfobar(INFOBAR, "LibreCharts", message, _INFOBAR_INFO)
            else:
                self.controller.appendInfobar(
                    INFOBAR, "LibreCharts", message, _INFOBAR_INFO, (), False
                )
        except Exception:  # no info bar (e.g. a hidden document): pick mode works without it
            traceback.print_exc()


def _single(selection: Any) -> Any:
    if selection is None or not hasattr(selection, "getCount") or selection.getCount() != 1:
        return None
    return selection.getByIndex(0)
