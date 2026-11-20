# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The 2x2 matrix dialog (M25): titles, end labels, quadrants, splits and bubbles."""

from __future__ import annotations

import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core import matrix as core_matrix
from librecharts.core.messages import text
from librecharts.core.model import ChartState, MatrixSpec
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
            values = ask(self.ctx, self.frame, state.matrix or MatrixSpec())
            if values is not None:
                changed = replace(
                    state, matrix=core_matrix.changed(state.matrix or MatrixSpec(), values)
                )
                chart.redraw(doc, self.group, changed)
        except Exception:
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, spec: MatrixSpec) -> dict[str, str] | None:
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
        self, dialog: Any, locale: str, spec: MatrixSpec, outcome: list[dict[str, str]]
    ) -> None:
        self.dialog, self.locale, self.spec, self.outcome = dialog, locale, spec, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            names = (
                "x_title",
                "y_title",
                "x_low",
                "x_high",
                "y_low",
                "y_high",
                "x_split",
                "y_split",
            )
            values = {name: str(self.dialog.getControl(name).getText()).strip() for name in names}
            values["quadrants"] = str(self.dialog.getControl("q0").getText()).strip()
            values["bubbles"] = "true" if self.dialog.getControl("bubbles").getState() else "false"
            values["labels"] = "true" if self.dialog.getControl("labels").getState() else "false"
            core_matrix.changed(self.spec, values)
            self.outcome.append(values)
            self.dialog.endExecute()
        except ValueError:
            self.dialog.getModel().getByName("error").Label = text(
                "matrix_options_invalid", self.locale
            )
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, spec: MatrixSpec) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("matrix_options_title", locale), 230, 260

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    fields = (
        ("x_title", "matrix_x_title", spec.x_title),
        ("y_title", "matrix_y_title", spec.y_title),
        ("x_low", "matrix_x_low", spec.x_low),
        ("x_high", "matrix_x_high", spec.x_high),
        ("y_low", "matrix_y_low", spec.y_low),
        ("y_high", "matrix_y_high", spec.y_high),
    )
    for index, (name, label, value) in enumerate(fields):
        y = 10 + index * 18
        add("FixedText", f"{name}_label", 10, y, 75, 10, Label=text(label, locale))
        add("Edit", name, 90, y - 2, 130, 12, Text=value)
    add("FixedText", "quadrants_label", 10, 120, 75, 10, Label=text("matrix_quadrants", locale))
    add(
        "Edit",
        "q0",
        90,
        118,
        130,
        12,
        Text="|".join(spec.quadrants),
    )
    add("FixedText", "x_split_label", 10, 138, 75, 10, Label=text("matrix_x_split", locale))
    add(
        "Edit",
        "x_split",
        90,
        136,
        130,
        12,
        Text="" if spec.x_split is None else f"{spec.x_split:g}",
    )
    add("FixedText", "y_split_label", 10, 156, 75, 10, Label=text("matrix_y_split", locale))
    add(
        "Edit",
        "y_split",
        90,
        154,
        130,
        12,
        Text="" if spec.y_split is None else f"{spec.y_split:g}",
    )
    add(
        "CheckBox",
        "bubbles",
        10,
        176,
        100,
        12,
        Label=text("matrix_bubbles", locale),
        State=1 if spec.bubbles else 0,
    )
    add(
        "CheckBox",
        "labels",
        120,
        176,
        100,
        12,
        Label=text("matrix_labels", locale),
        State=1 if spec.labels else 0,
    )
    add("FixedText", "error", 10, 192, 210, 20, Label="", TextColor=_RED, MultiLine=True)
    add("Button", "ok", 100, 226, 50, 14, Label=text("button_ok", locale), DefaultButton=True)
    add(
        "Button",
        "cancel",
        156,
        226,
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
