# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Pick one label of a chart to hide, retitle or reset (M22).

The renderer writes the label key into the shape name (``librecharts-label:<role>:<category>:
<series>``), so a selected child shape identifies its label without guessing from boxes. The
session enters the chart group like the annotation picker; ``Esc`` or a click outside cancels.
"""

from __future__ import annotations

import contextlib
import traceback
from typing import Any
from urllib.parse import urlencode

import unohelper
from com.sun.star.awt import XCallback, XKeyHandler
from com.sun.star.view import XSelectionChangeListener

from librecharts.core import labels
from librecharts.core.messages import text
from librecharts.core.state_io import StateError
from librecharts.lo import chart, store, textdialog, ui

INFOBAR = "org.librecharts.labelpick"
_INFOBAR_INFO = 1  # com.sun.star.frame.InfobarType.INFO
_ESCAPE = 1281  # com.sun.star.awt.Key.ESCAPE

_sessions: dict[str, _Pick] = {}


def start(ctx: Any, frame: Any, group: Any, command: str) -> None:
    """Let the user click one label of the chart in ``group`` for ``command``."""
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _sessions:
        _sessions[key].finish(None)
    _sessions[key] = _Pick(key, ctx, frame, group, command)


def active(doc: Any) -> bool:
    """Whether a label pick session is running in ``doc`` (for tests)."""
    return str(doc.RuntimeUID) in _sessions


class _Pick(unohelper.Base, XSelectionChangeListener, XKeyHandler, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any, group: Any, command: str) -> None:
        self.key, self.ctx, self.frame, self.group = key, ctx, frame, group
        self.command = command
        self.controller = frame.getController()
        self.chart_id = store.chart_id_of(group)
        self.locale = ui.ui_locale(ctx)
        self._done = False
        self._query: str | None = None
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        self.controller.select(group)
        ui.uno_command(ctx, frame, ".uno:EnterGroup")  # before listening: entering deselects
        self.controller.addSelectionChangeListener(self)
        self.controller.addKeyHandler(self)
        self._show_prompt()

    def finish(self, query: str | None) -> None:
        """End the session; apply ``query`` unless it is ``None`` (cancelled)."""
        if self._done:
            return
        self._done, self._query = True, query
        self._async.addCallback(self, None)  # None: void any, see lo/resize.py

    # XSelectionChangeListener
    def selectionChanged(self, event: Any) -> None:
        try:
            if self._done:
                return
            selection = self.controller.getSelection()
            if selection is None or not hasattr(selection, "getCount"):
                return
            if not selection.getCount():
                return
            shape = selection.getByIndex(0)
            if not self._in_chart(shape):
                self.finish(None)
                return
            key = labels.key_from_name(str(getattr(shape, "Name", "")))
            if key is None:
                return
            query = self._query_for(key, str(getattr(shape, "String", "")))
            if query is not None:
                self.finish(query)
        except Exception:
            # Never let an exception escape into LibreOffice's notification loop.
            traceback.print_exc()

    def _query_for(self, key: labels.LabelKey, current: str) -> str | None:
        parts = {"role": key.role, "category": str(key.category)}
        if key.series is not None:
            parts["series"] = str(key.series)
        if self.command == "SetLabelText":
            value = textdialog.ask_text(
                self.ctx, self.frame, "label_title", "label_text", current, limit=80
            )
            if value is None:
                return None
            parts["text"] = value
        elif self.command == "ResetLabel":
            pass
        else:
            parts["hidden"] = "true"
        return urlencode(parts)

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
            with contextlib.suppress(Exception):
                self.controller.removeSelectionChangeListener(self)
                self.controller.removeKeyHandler(self)
            with contextlib.suppress(Exception):
                if self.controller.hasInfobar(INFOBAR):
                    self.controller.removeInfobar(INFOBAR)
            ui.uno_command(self.ctx, self.frame, ".uno:LeaveGroup")
            if self._query is not None:
                doc = self.controller.getModel()
                chart_id = store.chart_id_of(self.group)
                state = store.read_state(doc, chart_id) if chart_id else None
                if state is not None:
                    changed = labels.override(state, self._query, command=self.command)
                    if changed != state:
                        chart.redraw(doc, self.group, changed)
            self.controller.select(self.group)
        except (StateError, ValueError):
            traceback.print_exc()
        except Exception:
            traceback.print_exc()

    def _in_chart(self, shape: Any) -> bool:
        try:
            return store.chart_id_of(shape.getParent()) == self.chart_id
        except AttributeError:
            return False

    def _show_prompt(self) -> None:
        message = text("label_pick_hint", self.locale)
        try:
            if self.controller.hasInfobar(INFOBAR):
                self.controller.updateInfobar(INFOBAR, "LibreCharts", message, _INFOBAR_INFO)
            else:
                self.controller.appendInfobar(
                    INFOBAR, "LibreCharts", message, _INFOBAR_INFO, (), False
                )
        except Exception:  # no info bar (e.g. a hidden document): picking works without it
            traceback.print_exc()
