# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Small UI helpers: the user's UI locale and message boxes."""

from __future__ import annotations

from typing import Any

import uno
from com.sun.star.beans import PropertyValue

_INFOBOX = uno.Enum("com.sun.star.awt.MessageBoxType", "INFOBOX")
_BUTTONS_OK = 1  # com.sun.star.awt.MessageBoxButtons.BUTTONS_OK


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


def show_info(ctx: Any, frame: Any, message: str) -> None:
    toolkit = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    box = toolkit.createMessageBox(
        frame.getContainerWindow(), _INFOBOX, _BUTTONS_OK, "LibreCharts", message
    )
    box.execute()
    box.dispose()
