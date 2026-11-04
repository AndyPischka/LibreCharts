# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The working-days dialog of a Gantt chart (M17): weekdays and holidays.

Opened asynchronously (an ``AsyncCallback``) so the command that asked for it returns first, like
the axis-break dialog. The dialog is built in code; validation lives in ``core/calendar.py``.
Modal dialogs cannot be driven by ``test-lo`` (headless LibreOffice returns from ``execute()`` at
once), so this module is tested by hand; everything behind it is tested without it.
"""

from __future__ import annotations

import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core.calendar import check_holidays
from librecharts.core.messages import text
from librecharts.core.model import Calendar, ChartState
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2  # com.sun.star.awt.PushButtonType.CANCEL
_RED = 0xCC0000

# Pending requests by presentation: a Python object passed to AsyncCallback must stay alive.
_requests: dict[str, _Request] = {}


def request(ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
    """Ask for the working days of the chart in ``group``, then store the answer."""
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
            choice = ask(self.ctx, self.frame, state.calendar)
            if choice is not None and choice != state.calendar:
                chart.redraw(doc, self.group, replace(state, calendar=choice))
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, current: Calendar) -> Calendar | None:
    """Show the dialog (modal); the chosen calendar, or ``None`` if cancelled."""
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale, current)
    outcome: list[Calendar] = []
    ok = _OkListener(dialog, locale, outcome)
    dialog.getControl("ok").addActionListener(ok)
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _OkListener(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, outcome: list[Calendar]) -> None:
        self.dialog, self.locale, self.outcome = dialog, locale, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            working = tuple(
                day for day in range(7) if self.dialog.getControl(f"day{day}").getState()
            )
            if not working:
                self._error("working_days_none")
                return
            holidays = check_holidays(self.dialog.getControl("holidays").getText(), self.locale)
            if isinstance(holidays, str):
                self._error(holidays)
                return
            self.outcome.append(Calendar(working, holidays))
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def _error(self, key: str) -> None:
        self.dialog.getModel().getByName("error").Label = text(key, self.locale)

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, current: Calendar) -> Any:
    """The dialog control, not yet shown. Sizes are in "Map AppFont" units."""
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("working_days_title", locale), 200, 150

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    names = text("working_days_names", locale).split(",")
    for day in range(7):
        add(
            "CheckBox",
            f"day{day}",
            10 + (day % 4) * 45,
            10 + (day // 4) * 14,
            44,
            12,
            Label=names[day],
            State=1 if day in current.working_days else 0,
            TabIndex=day,
        )
    add(
        "FixedText",
        "holidays_label",
        10,
        42,
        180,
        10,
        Label=text("working_days_holidays", locale),
        TabIndex=7,
    )
    add(
        "Edit",
        "holidays",
        10,
        54,
        180,
        50,
        Text="\n".join(day.isoformat() for day in current.holidays),
        MultiLine=True,
        VScroll=True,
        TabIndex=8,
    )
    add(
        "FixedText",
        "error",
        10,
        108,
        180,
        14,
        Label="",
        TextColor=_RED,
        MultiLine=True,
        TabIndex=9,
    )
    add(
        "Button",
        "ok",
        90,
        128,
        50,
        14,
        Label=text("button_ok", locale),
        DefaultButton=True,
        TabIndex=10,
    )
    add(
        "Button",
        "cancel",
        144,
        128,
        50,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
        TabIndex=11,
    )

    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    return dialog
