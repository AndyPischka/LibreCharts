# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The audit report with jump-to-slide (M29)."""

from __future__ import annotations

import traceback
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core.audit import Finding
from librecharts.core.messages import text

_PUSH_BUTTON_CANCEL = 2


def request(ctx: Any, frame: Any, findings: tuple[Finding, ...], locale: str) -> None:
    callback = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.AsyncCallback", ctx)
    callback.addCallback(_Dialog(ctx, frame, findings, locale), None)


class _Dialog(unohelper.Base, XCallback):
    def __init__(self, ctx: Any, frame: Any, findings: tuple[Finding, ...], locale: str) -> None:
        self.ctx, self.frame, self.findings, self.locale = ctx, frame, findings, locale

    def notify(self, data: Any) -> None:
        try:
            ask(self.ctx, self.frame, self.findings, self.locale)
        except Exception:
            traceback.print_exc()


def ask(ctx: Any, frame: Any, findings: tuple[Finding, ...], locale: str) -> None:
    dialog = _build(ctx, frame, locale, findings)
    dialog.getControl("go").addActionListener(_Go(dialog, frame, findings))
    try:
        dialog.execute()
    finally:
        dialog.dispose()


class _Go(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, frame: Any, findings: tuple[Finding, ...]) -> None:
        self.dialog, self.frame, self.findings = dialog, frame, findings

    def actionPerformed(self, event: Any) -> None:
        try:
            index = int(self.dialog.getControl("list").getSelectedItemPos())
            finding = self.findings[index]
            if finding.slide > 0:
                pages = self.frame.getController().getModel().getDrawPages()
                self.frame.getController().setCurrentPage(pages.getByIndex(finding.slide - 1))
            self.dialog.endExecute()
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, findings: tuple[Finding, ...]) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("menu_audit", locale), 300, 200

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    items = [
        text(
            "audit_list_item",
            locale,
            slide=str(finding.slide),
            message=text(finding.key, locale, detail=finding.detail),
        )
        for finding in findings
    ]
    add(
        "ListBox",
        "list",
        10,
        10,
        280,
        160,
        StringItemList=tuple(items),
        LineCount=10,
        Dropdown=False,
    )
    add("Button", "go", 80, 178, 70, 14, Label=text("audit_go", locale), DefaultButton=True)
    add(
        "Button",
        "close",
        156,
        178,
        70,
        14,
        Label=text("button_cancel", locale),
        PushButtonType=_PUSH_BUTTON_CANCEL,
    )
    dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dialog.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dialog.createPeer(toolkit, frame.getContainerWindow())
    return dialog
