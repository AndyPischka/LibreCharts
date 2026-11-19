"""Importing tabular data into a chart's data sheet (M28).

The extension accepts CSV text (from a file or the clipboard) and turns it into the same cell grid
the Calc data sheet uses: first row or first column headers, numbers where they parse. Reading ODS
and XLSX files needs LibreOffice and lives in ``lo/dataimport.py``.
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace

from librecharts.core.model import ChartState


class ImportError(ValueError):
    """The imported table cannot be used; ``key`` names the message."""

    def __init__(self, key: str = "import_invalid") -> None:
        super().__init__(key)
        self.key = key


def table(text_: str, delimiter: str = "") -> list[list[str]]:
    """Rows of cell strings from CSV text; the delimiter is guessed unless given."""
    sample = text_[:4096]
    if not delimiter:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(text_), delimiter=delimiter)
        if any(cell.strip() for cell in row)
    ]
    if not rows:
        raise ImportError("import_empty")
    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def state_with_table(state: ChartState, rows: list[list[str]]) -> ChartState:
    """``state`` with its data sheet replaced; numbers are parsed, other cells stay text."""
    if len(rows) < 2 or len(rows[0]) < 2:
        raise ImportError("import_too_small")
    cells = tuple(tuple(row) for row in rows)
    values = tuple(tuple(_number(cell) for cell in row) for row in rows)
    try:
        return replace(state, cells=cells, values=values, link=None)
    except ValueError as exc:
        raise ImportError("import_invalid") from exc


def _number(cell: str) -> float | None:
    text = cell.strip().replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None
