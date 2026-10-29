# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The document-wide colour scheme, stored as a custom property (ADR 0016).

The scheme JSON lives in ``librecharts:scheme`` next to the per-chart states, so it survives saving
as ODP and PPTX like them. A document without the property uses the configured default or the
built-in "Default" scheme. This module only reads and writes; changing the scheme with one undo
step is :func:`librecharts.lo.chart.set_scheme`.
"""

from __future__ import annotations

from typing import Any

import uno

from librecharts.core import style
from librecharts.core.model import ChartState
from librecharts.lo import render, store, ui

SETTINGS_PATH = "/org.librecharts.Settings"


def configured_default() -> style.Scheme:
    """The scheme for documents without their own: ``DefaultScheme`` from the extension config."""
    try:
        ctx = uno.getComponentContext()
        provider = ctx.getValueByName("/singletons/com.sun.star.configuration.theDefaultProvider")
        access = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess",
            (ui.prop("nodepath", SETTINGS_PATH),),
        )
        return style.built_in(str(access.DefaultScheme)) or style.DEFAULT
    except Exception:
        return style.DEFAULT


def load(doc: Any, fallback: style.Scheme | None = None) -> style.Scheme:
    """The document's colour scheme; ``fallback`` (the configured default) if none is stored."""
    text = store.read_property(doc, store.SCHEME_PROPERTY)
    if text is None:
        return fallback if fallback is not None else configured_default()
    try:
        return style.scheme_from_json(text)
    except style.SchemeError:
        return fallback if fallback is not None else configured_default()


def stored(doc: Any) -> bool:
    """Whether the document carries its own scheme property."""
    return store.read_property(doc, store.SCHEME_PROPERTY) is not None


def save(doc: Any, scheme: style.Scheme) -> None:
    """Store ``scheme`` in the document (no redraw, no undo action)."""
    store.write_property(doc, store.SCHEME_PROPERTY, style.scheme_to_json(scheme))


def look(doc: Any, state: ChartState, fallback: style.Scheme | None = None) -> render.Look:
    """The colours and font to draw ``state`` with: document scheme plus its series colours."""
    return render.Look(load(doc, fallback), state.colors)
