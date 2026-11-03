# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The group bracket label dialog (M14): the text a bracket shows over its categories.

Opened asynchronously for *Change text...* (an ``AsyncCallback``, like the axis break dialog), so
the command that asked for it returns first; after a pick session the caller asks directly.
Validation lives in ``core/annotations.check_bracket_text``. Modal dialogs cannot be driven by
``test-lo`` (headless LibreOffice returns from ``execute()`` at once), so this module is tested
by hand; everything behind it is tested without it.
"""

from __future__ import annotations

import traceback
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core import annotations
from librecharts.core.annotations import check_bracket_text
from librecharts.core.messages import text
from librecharts.core.model import ChartState
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2  # com.sun.star.awt.PushButtonType.CANCEL
_RED = 0xCC0000

# Pending requests by presentation: a Python object passed to AsyncCallback must stay alive.
_requests: dict[str, _Request] = {}


def ask(ctx: Any, frame: Any, initial: str) -> str | None:
    """Show the modal dialog; the trimmed label, or ``None`` if the user cancelled."""
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale, initial)
    outcome: list[str] = []
    ok = _OkListener(dialog, locale, outcome)
    dialog.getControl("ok").addActionListener(ok)
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


def request_edit(ctx: Any, frame: Any, group: Any, state: ChartState, index: int) -> None:
    """Ask for the text of the group bracket at ``index``, then change it; one undo step.

    Cancel changes nothing.
    """
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _requests:  # a dialog is already open
        return
    _requests[key] = _Request(key, ctx, frame, group, state, index)


class _Request(unohelper.Base, XCallback):
    def __init__(
        self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState, index: int
    ) -> None:
        self.key, self.ctx, self.frame, self.group = key, ctx, frame, group
        self.state, self.index = state, index
        callback = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        callback.addCallback(self, None)  # None: void any, see lo/resize.py

    def notify(self, data: Any) -> None:
        try:
            doc = self.frame.getController().getModel()
            # The user may have edited the chart since the command: start from the stored state.
            chart_id = store.chart_id_of(self.group)
            state = (store.read_state(doc, chart_id) if chart_id else None) or self.state
            annotations_of_state = state.annotations
            if self.index >= len(annotations_of_state):
                return
            current = annotations_of_state[self.index]
            if current.kind != "group_bracket":
                return
            label = ask(self.ctx, self.frame, current.text)
            if label is None or label == current.text:
                return
            query = f"index={self.index}&" + urlencode({"text": label})
            changed = annotations.changed(annotations_of_state, query)
            chart.redraw(doc, self.group, replace(state, annotations=changed))
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


class _OkListener(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, outcome: list[str]) -> None:
        self.dialog, self.locale, self.outcome = dialog, locale, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            label = self.dialog.getControl("label").getText().strip()
            error = check_bracket_text(label)
            if error is not None:  # keep the dialog open and say what is wrong
                self.dialog.getModel().getByName("error").Label = text(error, self.locale)
                return
            self.outcome.append(label)
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, initial: str) -> Any:
    """The dialog control, not yet shown. Sizes are in "Map AppFont" units."""
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("bracket_title", locale), 190, 72

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    add("FixedText", "label_label", 10, 10, 170, 10, Label=text("bracket_text", locale), TabIndex=0)
    add("Edit", "label", 10, 24, 170, 12, Text=initial, TabIndex=1)
    add("FixedText", "error", 10, 42, 170, 10, Label="", TextColor=_RED, TabIndex=2)
    add(
        "Button",
        "ok",
        80,
        54,
        50,
        14,
        Label=text("button_ok", locale),
        DefaultButton=True,
        TabIndex=3,
    )
    add(
        "Button",
        "cancel",
        134,
        54,
        50,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
        TabIndex=4,
    )

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    return dialog
