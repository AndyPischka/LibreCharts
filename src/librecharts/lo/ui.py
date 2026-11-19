# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Small UI helpers: the user's UI locale, message boxes and LibreOffice commands."""

from __future__ import annotations

import contextlib
from typing import Any

import uno
from com.sun.star.beans import PropertyValue

_INFOBOX = uno.Enum("com.sun.star.awt.MessageBoxType", "INFOBOX")
_QUERYBOX = uno.Enum("com.sun.star.awt.MessageBoxType", "QUERYBOX")
_BUTTONS_OK = 1  # com.sun.star.awt.MessageBoxButtons.BUTTONS_OK
_BUTTONS_YES_NO = 3  # com.sun.star.awt.MessageBoxButtons.BUTTONS_YES_NO
_RESULT_YES = 2  # com.sun.star.awt.MessageBoxResults.YES


def prop(name: str, value: Any) -> PropertyValue:
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def ui_locale(ctx: Any) -> str:
    """LibreOffice's UI locale, e.g. ``de-DE``; empty if it cannot be read."""
    try:
        provider = ctx.getValueByName("/singletons/com.sun.star.configuration.theDefaultProvider")
        access = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess",
            (prop("nodepath", "/org.openoffice.Setup/L10N"),),
        )
        return str(access.ooLocale or "")
    except Exception:
        return ""


def uno_command(ctx: Any, frame: Any, command: str) -> None:
    """Dispatch a LibreOffice command such as ``.uno:EnterGroup`` in ``frame``."""
    helper = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    helper.executeDispatch(frame, command, "", 0, ())


def show_info(ctx: Any, frame: Any, message: str) -> None:
    toolkit = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    box = toolkit.createMessageBox(
        frame.getContainerWindow(), _INFOBOX, _BUTTONS_OK, "LibreCharts", message
    )
    box.execute()
    box.dispose()


def tell(ctx: Any, frame: Any, message: str) -> None:
    """Show ``message`` in a box, or print it where there is no window (headless, hidden docs)."""
    window = None
    with contextlib.suppress(Exception):
        window = frame.getContainerWindow()
    if window is None or not window.isVisible():
        print(message)
        return
    show_info(ctx, frame, message)


def ask(ctx: Any, frame: Any, message: str) -> bool:
    """Ask a yes/no question; ``False`` where there is no window to ask in (headless)."""
    window = None
    with contextlib.suppress(Exception):
        window = frame.getContainerWindow()
    if window is None or not window.isVisible():
        print(message)
        return False
    toolkit = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    box = toolkit.createMessageBox(window, _QUERYBOX, _BUTTONS_YES_NO, "LibreCharts", message)
    try:
        return box.execute() == _RESULT_YES
    finally:
        box.dispose()
