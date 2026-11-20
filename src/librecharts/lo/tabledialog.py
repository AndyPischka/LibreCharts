# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The table options dialog (M25): header, zebra, borders, heatmap, widths and row height."""

from __future__ import annotations

import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core import table as core_table
from librecharts.core.messages import text
from librecharts.core.model import ChartState, TableSpec
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2
_RED = 0xCC0000
_requests: dict[str, _Request] = {}


def request(ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _requests:
        return
    _requests[key] = _Request(key, ctx, frame, group, state)


class _Request(unohelper.Base, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState) -> None:
        self.key, self.ctx, self.frame, self.group, self.state = key, ctx, frame, group, state
        callback = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        callback.addCallback(self, None)

    def notify(self, data: Any) -> None:
        try:
            doc = self.frame.getController().getModel()
            chart_id = store.chart_id_of(self.group)
            state = (store.read_state(doc, chart_id) if chart_id else None) or self.state
            values = ask(self.ctx, self.frame, state.table or TableSpec())
            if values is not None:
                changed = replace(
                    state, table=core_table.changed(state.table or TableSpec(), values)
                )
                chart.redraw(doc, self.group, changed)
        except Exception:
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, spec: TableSpec) -> dict[str, str] | None:
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale, spec)
    outcome: list[dict[str, str]] = []
    ok = _Ok(dialog, locale, spec, outcome)
    dialog.getControl("ok").addActionListener(ok)
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _Ok(unohelper.Base, XActionListener):
    def __init__(
        self, dialog: Any, locale: str, spec: TableSpec, outcome: list[dict[str, str]]
    ) -> None:
        self.dialog, self.locale, self.spec, self.outcome = dialog, locale, spec, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            values = {
                "header": "true" if self.dialog.getControl("header").getState() else "false",
                "first_column": "true"
                if self.dialog.getControl("first_column").getState()
                else "false",
                "zebra": "true" if self.dialog.getControl("zebra").getState() else "false",
                "borders": "true" if self.dialog.getControl("borders").getState() else "false",
                "heatmap": "true" if self.dialog.getControl("heatmap").getState() else "false",
                "widths": str(self.dialog.getControl("widths").getText()).strip(),
                "row_height": str(self.dialog.getControl("row_height").getText()).strip(),
            }
            core_table.changed(self.spec, values)
            self.outcome.append(values)
            self.dialog.endExecute()
        except ValueError:
            self.dialog.getModel().getByName("error").Label = text(
                "table_options_invalid", self.locale
            )
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, spec: TableSpec) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("table_options_title", locale), 210, 180

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    for index, (name, label, value) in enumerate(
        (
            ("header", "table_header", spec.header),
            ("first_column", "table_first_column", spec.first_column),
            ("zebra", "table_zebra", spec.zebra),
            ("borders", "table_borders", spec.borders),
            ("heatmap", "table_heatmap", spec.heatmap),
        )
    ):
        add(
            "CheckBox",
            name,
            10 + (index % 2) * 100,
            10 + (index // 2) * 16,
            95,
            12,
            Label=text(label, locale),
            State=1 if value else 0,
        )
    add("FixedText", "widths_label", 10, 54, 80, 10, Label=text("table_widths", locale))
    add("Edit", "widths", 95, 52, 105, 12, Text=",".join(f"{w:g}" for w in spec.widths))
    add("FixedText", "row_height_label", 10, 70, 80, 10, Label=text("table_row_height", locale))
    add(
        "Edit",
        "row_height",
        95,
        68,
        105,
        12,
        Text="" if spec.row_height is None else f"{spec.row_height:g}",
    )
    add("FixedText", "error", 10, 86, 190, 20, Label="", TextColor=_RED, MultiLine=True)
    add("Button", "ok", 90, 120, 50, 14, Label=text("button_ok", locale), DefaultButton=True)
    add(
        "Button",
        "cancel",
        146,
        120,
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
