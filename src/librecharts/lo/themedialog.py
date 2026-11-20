# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The palette and font dialog (M30): change one palette entry and the scheme font."""

from __future__ import annotations

import traceback
from typing import Any

import unohelper
from com.sun.star.awt import XActionListener, XCallback

from librecharts.core import style
from librecharts.core.messages import text
from librecharts.lo import chart, scheme

_PUSH_BUTTON_CANCEL = 2
_RED = 0xCC0000


def request(ctx: Any, frame: Any) -> None:
    callback = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.AsyncCallback", ctx)
    callback.addCallback(_Dialog(ctx, frame), None)


class _Dialog(unohelper.Base, XCallback):
    def __init__(self, ctx: Any, frame: Any) -> None:
        self.ctx, self.frame = ctx, frame

    def notify(self, data: Any) -> None:
        try:
            doc = self.frame.getController().getModel()
            current = scheme.load(doc)
            values = ask(self.ctx, self.frame, current)
            if values is not None:
                index, colour, name, size = values
                changed = style.with_palette(current, index, colour)
                changed = style.with_font(changed, name, size)
                chart.set_scheme(doc, changed)
        except Exception:
            traceback.print_exc()


def ask(ctx: Any, frame: Any, current: style.Scheme) -> tuple[int, int, str, float] | None:
    locale = ui_locale(ctx)
    dialog = _build(ctx, frame, locale, current)
    outcome: list[tuple[int, int, str, float]] = []
    dialog.getControl("ok").addActionListener(_Ok(dialog, locale, outcome))
    try:
        dialog.execute()
    finally:
        dialog.dispose()
    return outcome[0] if outcome else None


class _Ok(unohelper.Base, XActionListener):
    def __init__(self, dialog: Any, locale: str, outcome: list[Any]) -> None:
        self.dialog, self.locale, self.outcome = dialog, locale, outcome

    def actionPerformed(self, event: Any) -> None:
        try:
            index = int(self.dialog.getControl("index").getText())
            colour = int(self.dialog.getControl("colour").getText().strip().lstrip("#"), 16)
            name = str(self.dialog.getControl("font").getText()).strip()
            size = float(self.dialog.getControl("size").getText().replace(",", "."))
            style.with_palette(style.DEFAULT, index, colour)
            self.outcome.append((index, colour, name, size))
            self.dialog.endExecute()
        except ValueError:
            self.dialog.getModel().getByName("error").Label = text("theme_invalid", self.locale)
        except Exception:
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        pass


def _build(ctx: Any, frame: Any, locale: str, current: style.Scheme) -> Any:
    smgr = ctx.ServiceManager
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    model.Title, model.Width, model.Height = text("theme_title", locale), 200, 160

    def add(kind: str, name: str, x: int, y: int, width: int, height: int, **props: Any) -> None:
        control = model.createInstance(f"com.sun.star.awt.UnoControl{kind}Model")
        model.insertByName(name, control)
        control.PositionX, control.PositionY = x, y
        control.Width, control.Height = width, height
        for prop, value in props.items():
            setattr(control, prop, value)

    add("FixedText", "index_label", 10, 12, 70, 10, Label=text("theme_index", locale))
    add("Edit", "index", 85, 10, 100, 12, Text="0")
    add("FixedText", "colour_label", 10, 30, 70, 10, Label=text("theme_colour", locale))
    add("Edit", "colour", 85, 28, 100, 12, Text=f"{current.palette[0]:06X}")
    add("FixedText", "font_label", 10, 48, 70, 10, Label=text("theme_font", locale))
    add("Edit", "font", 85, 46, 100, 12, Text=current.font_name)
    add("FixedText", "size_label", 10, 66, 70, 10, Label=text("theme_size", locale))
    add("Edit", "size", 85, 64, 100, 12, Text=f"{current.font_size:g}")
    add("FixedText", "error", 10, 84, 180, 20, Label="", TextColor=_RED, MultiLine=True)
    add("Button", "ok", 70, 120, 50, 14, Label=text("button_ok", locale), DefaultButton=True)
    add(
        "Button",
        "cancel",
        126,
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


def ui_locale(ctx: Any) -> str:
    from librecharts.lo import ui

    return ui.ui_locale(ctx)
