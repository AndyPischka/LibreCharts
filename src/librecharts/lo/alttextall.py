# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Give every shape without alternative text a short description (M30)."""

from __future__ import annotations

from typing import Any

from librecharts.core.messages import text


def apply(ctx: Any, doc: Any) -> int:
    """Set missing titles and descriptions; returns how many shapes changed."""
    changed = 0
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for child in range(page.getCount()):
            shape = page.getByIndex(child)
            if not str(getattr(shape, "Description", "")):
                label = _label(shape)
                shape.Description = label
                if not str(getattr(shape, "Title", "")):
                    shape.Title = label
                changed += 1
    return changed


def _label(shape: Any) -> str:
    for attribute in ("String", "Text"):
        try:
            value = str(getattr(shape, attribute))
        except AttributeError:
            continue
        if value.strip():
            return value.strip()[:120]
    kind = str(getattr(shape, "ShapeType", "shape")).rsplit(".", 1)[-1]
    return text("alt_shape", "en", kind=kind)


def locale_note() -> str:
    return text("alt_shape", "en", kind="shape")
