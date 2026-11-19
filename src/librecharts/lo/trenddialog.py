# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The trendline dialog (M23): series, kind, forecast and the R²/equation labels."""

from __future__ import annotations

import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core.messages import text
from librecharts.core.model import ChartState, Trend
from librecharts.lo import chart, store, ui

_PUSH_BUTTON_CANCEL = 2
_RED = 0xCC0000
_requests: dict[str, _Request] = {}


def request(ctx: Any, frame: Any, group: Any, state: ChartState, series: int | None) -> None:
    key = str(frame.getController().getModel().RuntimeUID)
    if key in _requests:
        return
    _requests[key] = _Request(key, ctx, frame, group, state, series)


class _Request(unohelper.Base, XCallback):
    def __init__(
        self, key: str, ctx: Any, frame: Any, group: Any, state: ChartState, series: int | None
    ) -> None:
        self.key, self.ctx, self.frame, self.group = key, ctx, frame, group
        self.state, self.series = state, series
        callback = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        callback.addCallback(self, None)

    def notify(self, data: Any) -> None:
        try:
            doc = self.frame.getController().getModel()
            chart_id = store.chart_id_of(self.group)
            state = (store.read_state(doc, chart_id) if chart_id else None) or self.state
            trend = ask(self.ctx, self.frame, state, self.series)
            if trend is not None:
                chart.redraw(
                    doc,
                    self.group,
                    replace(
                        state,
                        trends=(
                            *(item for item in state.trends if item.series != trend.series),
                            trend,
                        ),
                    ),
                )
        except Exception:
            traceback.print_exc()
        finally:
            _requests.pop(self.key, None)


def ask(ctx: Any, frame: Any, state: ChartState, series: int | None) -> Trend | None:
    locale = ui.ui_locale(ctx)
    dialog = _build(ctx, frame, locale, state, series)
    outcome: list[Trend] = []
    ok = _Ok(dialog, locale, outcome)
    dialog.getControl("ok").addActionListener(ok)
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _Ok(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, outcome: list[Trend]) -> None:
        self.dialog, self.locale, self.outcome = dialog, locale, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            series = int(self.dialog.getControl("series").getText())
            forecast = int(self.dialog.getControl("forecast").getText() or "0")
            kind = "exponential" if self.dialog.getControl("exponential").getState() else "linear"
            self.outcome.append(
                Trend(
                    series,
                    kind,  # pyright: ignore[reportArgumentType]
                    forecast,
                    bool(self.dialog.getControl("r2").getState()),
                    bool(self.dialog.getControl("equation").getState()),
                )
            )
            self.dialog.endExecute()
        except ValueError:
            self.dialog.getModel().getByName("error").Label = text("trend_invalid", self.locale)
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, state: ChartState, series: int | None) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("trend_title", locale), 190, 138

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    add("FixedText", "series_label", 10, 10, 80, 10, Label=text("trend_series", locale))
    add("Edit", "series", 100, 8, 80, 12, Text=str(series or 0))
    add("RadioButton", "linear", 10, 28, 80, 10, Label=text("trend_linear", locale), State=1)
    add("RadioButton", "exponential", 100, 28, 80, 10, Label=text("trend_exponential", locale))
    add("FixedText", "forecast_label", 10, 46, 80, 10, Label=text("trend_forecast", locale))
    add("Edit", "forecast", 100, 44, 80, 12, Text="0")
    add("CheckBox", "r2", 10, 62, 80, 10, Label=text("trend_show_r2", locale), State=1)
    add("CheckBox", "equation", 100, 62, 80, 10, Label=text("trend_show_equation", locale))
    add("FixedText", "error", 10, 78, 170, 20, Label="", TextColor=_RED, MultiLine=True)
    add("Button", "ok", 80, 110, 50, 14, Label=text("button_ok", locale), DefaultButton=True)
    add(
        "Button",
        "cancel",
        134,
        110,
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
