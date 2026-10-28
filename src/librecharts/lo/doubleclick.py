# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Double-click on a chart opens its data sheet instead of entering the group.

One mouse click handler per presentation, registered by the document-open job and by the
LibreCharts commands. The first click of a double-click selects the chart; on the second press the
handler swallows the event (so Impress does not enter the group) and opens the data sheet
asynchronously, outside the mouse event processing. Double-clicks on anything else, or inside a
group the user entered, pass through untouched.
"""

from __future__ import annotations

import traceback
from typing import Any

import unohelper
from com.sun.star.awt import XCallback, XMouseClickHandler

from librecharts.lo import commands

_LEFT = 1  # com.sun.star.awt.MouseButton.LEFT

_handlers: dict[str, _Handler] = {}


def attach(ctx: Any, frame: Any) -> None:
    """Handle double-clicks in the view of ``frame`` (idempotent per presentation)."""
    controller = frame.getController()
    key = str(controller.getModel().RuntimeUID)
    if key not in _handlers:
        handler = _Handler(key, ctx, frame)
        controller.addMouseClickHandler(handler)
        _handlers[key] = handler


class _Handler(unohelper.Base, XMouseClickHandler, XCallback):
    def __init__(self, key: str, ctx: Any, frame: Any) -> None:
        self.key, self.ctx, self.frame = key, ctx, frame
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )

    # XMouseClickHandler
    def mousePressed(self, event: Any) -> bool:
        try:
            if event.Buttons != _LEFT or event.ClickCount != 2:
                return False
            if commands.selected_chart(self.frame.getController()) is None:
                return False
            self._async.addCallback(self, None)  # None: void any, see lo/resize.py
            return True  # swallow it: Impress would enter the group
        except Exception:
            # Never let an exception escape into the event handling of LibreOffice.
            traceback.print_exc()
            return False

    def mouseReleased(self, event: Any) -> bool:
        return False

    def disposing(self, event: Any) -> None:
        _handlers.pop(self.key, None)

    # XCallback
    def notify(self, data: Any) -> None:
        try:
            commands.edit_data(self.ctx, self.frame)
        except Exception:
            traceback.print_exc()
