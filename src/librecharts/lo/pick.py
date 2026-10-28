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
from typing import Any

import unohelper
from com.sun.star.awt import XCallback, XKeyHandler
from com.sun.star.view import XSelectionChangeListener

from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState
from librecharts.core.picking import PickSession, target_at
from librecharts.lo import chart, store, ui

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
        _uno_command(ctx, frame, ".uno:EnterGroup")  # before listening: entering deselects
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
            position, size, origin = shape.Position, shape.Size, self.group.Position
            if self._is_frame(position, size):
                return
            target = target_at(
                self.state,
                self.group.Size.Width,
                self.group.Size.Height,
                position.X - origin.X + size.Width / 2,
                position.Y - origin.Y + size.Height / 2,
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
            _uno_command(self.ctx, self.frame, ".uno:LeaveGroup")
            if self._result is not None:
                chart.add_annotation(self.controller.getModel(), self.group, self._result)
            self.controller.select(self.group)
        except Exception:
            traceback.print_exc()

    def _in_chart(self, shape: Any) -> bool:
        try:
            return store.chart_id_of(shape.getParent()) == self.chart_id
        except AttributeError:  # not a shape inside a group
            return False

    def _is_frame(self, position: Any, size: Any) -> bool:
        origin, extent = self.group.Position, self.group.Size
        return all(
            abs(a - b) <= _TOLERANCE
            for a, b in (
                (position.X, origin.X),
                (position.Y, origin.Y),
                (size.Width, extent.Width),
                (size.Height, extent.Height),
            )
        )

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


def _uno_command(ctx: Any, frame: Any, command: str) -> None:
    helper = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    helper.executeDispatch(frame, command, "", 0, ())
