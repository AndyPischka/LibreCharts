# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Reading CSV, ODS and XLSX into a DataTable for a chart (M28)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import uno

from librecharts.core import importdata


def read_file(ctx: Any, location: str, sheet: str = "") -> list[list[str]]:
    """The first (or named) sheet of a spreadsheet or a CSV file as cell strings."""
    path = uno.fileUrlToSystemPath(location) if location.startswith("file:") else location
    suffix = Path(path).suffix.lower()
    if suffix in (".csv", ".txt", ".tsv"):
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        return importdata.table(text)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    url = location if location.startswith("file:") else Path(path).as_uri()
    doc = desktop.loadComponentFromURL(url, "_blank", 0, (_hidden(),))
    try:
        sheets = doc.getSheets()
        chosen = (
            sheets.getByName(sheet) if sheet and sheets.hasByName(sheet) else sheets.getByIndex(0)
        )
        cursor = chosen.createCursor()
        cursor.gotoEndOfUsedArea(False)
        last_column = cursor.RangeAddress.EndColumn
        last_row = cursor.RangeAddress.EndRow
        rows: list[list[str]] = []
        for row in range(last_row + 1):
            rows.append(
                [
                    str(chosen.getCellByPosition(column, row).getString())
                    for column in range(last_column + 1)
                ]
            )
        return rows
    finally:
        doc.close(True)


def _hidden() -> Any:
    value = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    value.Name, value.Value = "Hidden", True
    return value


def clipboard_text(ctx: Any) -> str:
    """The text on the system clipboard (empty if there is none)."""
    try:
        clipboard = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.datatransfer.clipboard.SystemClipboard", ctx
        )
        transferable = clipboard.getContents()
        if transferable is None:
            return ""
        for flavor in transferable.getTransferDataFlavors():
            if "text/plain" in flavor.MimeType:
                return str(transferable.getTransferData(flavor))
    except Exception:
        return ""
    return ""
