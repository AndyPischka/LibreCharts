# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The axis break dialog: automatic, or a lower and an upper value to remove from the scale.

Opened asynchronously (an ``AsyncCallback``) so the command that asked for it returns first. The
dialog is built in code, no resource file to ship. Validation lives in ``core/axis_break.py``.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback, XItemListener

from librecharts.core.axis_break import check, limit, suggestion
from librecharts.core.layout.common import format_value
from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2  # com.sun.star.awt.PushButtonType.CANCEL
_RED = 0xCC0000

# Pending requests by presentation: a Python object passed to AsyncCallback must stay alive.
_requests: dict[str, _Request] = {}


@dataclass(frozen=True, slots=True)
class Choice:
    """What the user chose; ``lower`` and ``upper`` are ``None`` for automatic."""

    lower: float | None
    upper: float | None


def request(ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
    """Ask the user about the axis break of the chart in ``group``, then store the answer.

    The dialog shows the current break of ``state`` if it has one. Cancel changes nothing.
    """
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _requests:  # a dialog is already open
        return
    _requests[key] = _Request(key, ctx, frame, group, state)


class _Request(unohelper.Base, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
        self.key, self.ctx, self.frame, self.group, self.state = key, ctx, frame, group, state
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
            current = next((a for a in reversed(state.annotations) if a.kind == "axis_break"), None)
            choice = ask(self.ctx, self.frame, state, current)
            if choice is not None:
                annotation = Annotation("axis_break", 0, 0, lower=choice.lower, upper=choice.upper)
                chart.add_annotation(doc, self.group, annotation)
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, state: ChartState, current: Annotation | None) -> Choice | None:
    """Show the dialog (modal); the choice, or ``None`` if cancelled."""
    locale = ui.ui_locale(ctx)
    tallest = limit(state)
    shown = current if current and current.lower is not None else None
    if shown is None and (proposal := suggestion(state)) is not None:
        lower, upper = proposal.lower, proposal.upper
    elif shown is not None and shown.lower is not None and shown.upper is not None:
        lower, upper = shown.lower, shown.upper
    else:
        lower = upper = None
    dialog = _build(
        ctx,
        frame,
        locale,
        manual=shown is not None,
        lower="" if lower is None else format_value(lower),
        upper="" if upper is None else format_value(upper),
        tallest=format_value(tallest),
    )
    outcome: list[Choice] = []
    ok = _OkListener(dialog, locale, tallest, outcome)
    dialog.getControl("ok").addActionListener(ok)
    dialog.getControl("manual").addItemListener(_RadioListener(dialog))
    dialog.getControl("auto").addItemListener(_RadioListener(dialog))
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _RadioListener(unohelper.Base, XItemListener):
    """Enables the two value fields only while "manual" is chosen."""

    def __init__(self, dialog: Any) -> None:
        self.dialog = dialog

    def itemStateChanged(self, event: Any) -> None:
        try:
            _sync_fields(self.dialog)
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


class _OkListener(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, tallest: float, outcome: list[Choice]) -> None:
        self.dialog, self.locale, self.tallest, self.outcome = dialog, locale, tallest, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            if self.dialog.getControl("auto").getState():
                self.outcome.append(Choice(None, None))
                self.dialog.endExecute()
                return
            checked = check(
                self.dialog.getControl("lower").getText(),
                self.dialog.getControl("upper").getText(),
                self.tallest,
            )
            if isinstance(checked, str):  # keep the dialog open and say what is wrong
                self.dialog.getModel().getByName("error").Label = text(checked, self.locale)
                return
            self.outcome.append(Choice(*checked))
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _sync_fields(dialog: Any) -> None:
    manual = bool(dialog.getControl("manual").getState())
    for name in ("lower", "upper", "lower_label", "upper_label"):
        dialog.getModel().getByName(name).Enabled = manual


def _build(
    ctx: Any, frame: Any, locale: str, *, manual: bool, lower: str, upper: str, tallest: str
) -> Any:
    """The dialog control, not yet shown. Sizes are in "Map AppFont" units."""
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("break_title", locale), 190, 126

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    # The tab order makes the two radio buttons one group.
    add(
        "RadioButton",
        "auto",
        10,
        10,
        170,
        10,
        Label=text("break_auto", locale),
        State=0 if manual else 1,
        TabIndex=0,
    )
    add(
        "RadioButton",
        "manual",
        10,
        25,
        170,
        10,
        Label=text("break_manual", locale),
        State=1 if manual else 0,
        TabIndex=1,
    )
    add("FixedText", "lower_label", 24, 42, 70, 10, Label=text("break_lower", locale), TabIndex=2)
    add("Edit", "lower", 100, 40, 70, 12, Text=lower, TabIndex=3)
    add("FixedText", "upper_label", 24, 58, 70, 10, Label=text("break_upper", locale), TabIndex=4)
    add("Edit", "upper", 100, 56, 70, 12, Text=upper, TabIndex=5)
    add(
        "FixedText",
        "hint",
        10,
        76,
        170,
        10,
        Label=text("break_hint", locale, tallest=tallest),
        TabIndex=6,
    )
    add("FixedText", "error", 10, 88, 170, 18, Label="", TextColor=_RED, MultiLine=True, TabIndex=7)
    add(
        "Button",
        "ok",
        80,
        108,
        50,
        14,
        Label=text("button_ok", locale),
        DefaultButton=True,
        TabIndex=8,
    )
    add(
        "Button",
        "cancel",
        134,
        108,
        50,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
        TabIndex=9,
    )

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    _sync_fields(dialog)
    return dialog
