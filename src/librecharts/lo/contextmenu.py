# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The LibreCharts submenu in the context menu of a selected chart (contents: core/menu.py).

One interceptor per presentation, registered by the document-open job and by the LibreCharts
commands, like the double-click handler. The menu cannot tell which column was right-clicked
(the selection is the whole chart), so it offers commands for the chart and its annotations.
"""

from __future__ import annotations

import traceback
from typing import Any

import uno
import unohelper
from com.sun.star.ui import XContextMenuInterceptor

from librecharts.core.menu import MenuItem, chart_menu
from librecharts.lo import commands, scheme, store, ui

_IGNORED = uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "IGNORED")
_EXECUTE_MODIFIED = uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "EXECUTE_MODIFIED")
_SEPARATOR_LINE = 0  # com.sun.star.ui.ActionTriggerSeparatorType.LINE

_attached: set[str] = set()


def attach(ctx: Any, frame: Any) -> None:
    """Add the LibreCharts submenu to context menus in the view of ``frame`` (idempotent)."""
    controller = frame.getController()
    key = str(controller.getModel().RuntimeUID)
    if key not in _attached:
        controller.registerContextMenuInterceptor(_Interceptor(ctx, controller))
        _attached.add(key)


class _Interceptor(unohelper.Base, XContextMenuInterceptor):
    def __init__(self, ctx: Any, controller: Any) -> None:
        self.ctx, self.controller = ctx, controller

    def notifyContextMenuExecute(self, event: Any) -> Any:
        try:
            group = commands.selected_chart(self.controller)
            if group is None:
                return _IGNORED
            doc = self.controller.getModel()
            chart_id = store.resolve(doc, group)
            state = store.read_state(doc, chart_id) if chart_id else None
            if state is None:  # orphaned: the menu commands would only say so
                return _IGNORED
            container = event.ActionTriggerContainer
            palette = scheme.load(doc).palette
            _insert(container, 0, chart_menu(state, ui.ui_locale(self.ctx), palette))
            _insert(container, 1, MenuItem())
            return _EXECUTE_MODIFIED
        except Exception:
            # Never let an exception escape into LibreOffice's menu handling.
            traceback.print_exc()
            return _IGNORED


def _insert(container: Any, index: int, item: MenuItem) -> None:
    if not item.title:
        entry = container.createInstance("com.sun.star.ui.ActionTriggerSeparator")
        entry.setPropertyValue("SeparatorType", _SEPARATOR_LINE)
    else:
        entry = container.createInstance("com.sun.star.ui.ActionTrigger")
        entry.setPropertyValue("Text", item.title)
        if item.children:
            sub = container.createInstance("com.sun.star.ui.ActionTriggerContainer")
            for i, child in enumerate(item.children):
                _insert(sub, i, child)
            entry.setPropertyValue("SubContainer", sub)
        else:
            entry.setPropertyValue("CommandURL", item.command)
    # A plain Python object is not accepted as the ``any`` argument (spike, M4 plan).
    uno.invoke(
        container, "insertByIndex", (index, uno.Any("com.sun.star.beans.XPropertySet", entry))
    )
