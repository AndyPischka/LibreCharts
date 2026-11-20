# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The icon picker (M26): choose one of the built-in icon names."""

from __future__ import annotations

import traceback
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener

from librecharts.core import icons
from librecharts.core.messages import text
from librecharts.lo import ui

_PUSH_BUTTON_CANCEL = 2


def ask(ctx: Any, frame: Any) -> str | None:
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale)
    outcome: list[str] = []
    dialog.getControl("ok").addActionListener(_Ok(dialog, locale, outcome))
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _Ok(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, outcome: list[str]) -> None:
        self.dialog, self.locale, self.outcome = dialog, locale, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            index = self.dialog.getControl("icons").getSelectedItemPos()
            self.outcome.append(icons.ICONS[index])
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("insert_icon", locale), 190, 230

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    add(
        "ListBox",
        "icons",
        10,
        10,
        170,
        180,
        StringItemList=icons.ICONS,
        LineCount=10,
        Dropdown=False,
    )
    add("Button", "ok", 60, 200, 50, 14, Label=text("button_ok", locale), DefaultButton=True)
    add(
        "Button",
        "cancel",
        114,
        200,
        50,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
    )
    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    return dialog
