"""Chart data as CSV (M20, ADR 0030).

The export writes the data sheet as the chart stores it: every row and column, the evaluated value
of a number cell and the text of any other cell, so a formula exports its result. The dialect
follows the chart's decimal separator, the way spreadsheets expect it: a decimal point goes with
commas between the fields, a decimal comma with semicolons. A Gantt chart's date columns export
ISO dates (``2026-06-30``), which every spreadsheet reads. Pure Python, no UNO.
"""

from __future__ import annotations

import csv
import io
import math
from decimal import Decimal

from librecharts.core.gantt import pairs, to_date
from librecharts.core.model import ChartState

DEFAULT_NAME = "chart-data.csv"


def delimiter(state: ChartState) -> str:
    """``";"`` for a chart with a decimal comma, else ``","``."""
    return ";" if state.format.separator == "," else ","


def to_csv(state: ChartState) -> str:
    """The data sheet of ``state`` as CSV text (lines end with CRLF, as RFC 4180 has it)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=delimiter(state), lineterminator="\r\n")
    for row in rows(state):
        writer.writerow(row)
    return out.getvalue()


def rows(state: ChartState) -> list[list[str]]:
    """The cells of the data sheet as text, trailing empty rows and columns dropped."""
    width = max((len(row) for row in state.cells), default=0)
    dates = _date_columns(state, width)
    table: list[list[str]] = []
    for r, cells in enumerate(state.cells):
        values = state.values[r] if r < len(state.values) else ()
        table.append(
            [
                _cell(
                    cells[c] if c < len(cells) else "",
                    values[c] if c < len(values) else None,
                    state,
                    r > 0 and c in dates,
                )
                for c in range(width)
            ]
        )
    while table and not any(cell.strip() for cell in table[-1]):
        table.pop()
    while table and table[0] and not any(row[-1].strip() for row in table):
        for row in table:
            row.pop()
    return table


def _date_columns(state: ChartState, width: int) -> frozenset[int]:
    if state.kind != "gantt":
        return frozenset()
    return frozenset(column for pair in pairs(width) for column in pair)


def _cell(raw: str, value: float | None, state: ChartState, is_date: bool) -> str:
    if value is None or not math.isfinite(value):
        return raw
    if is_date and (day := to_date(value)) is not None:
        return day.isoformat()
    return number(value, state.format.separator)


def number(value: float, separator: str = ".") -> str:
    """A value without loss and without exponent: ``12``, ``0.125``, ``-3,5`` with a comma."""
    if value == int(value) and abs(value) < 1e15:
        text = str(int(value))
    else:
        text = format(Decimal(repr(value)), "f")  # the shortest exact digits, never an exponent
        if "." in text:
            text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",") if separator == "," else text
