"""Data sheet conventions: turn a table of cells into chart data (and back for sample data).

Layout, like think-cell: the first row holds category names, the first column holds series names,
the top-left cell is unused. Every following row is one series, every following column one category.

Category and series names are taken from the raw cell contents, so a formula in a header cell
shows up as its text. Only the value grid is evaluated by Calc.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from librecharts.core.model import ChartKind, ChartState, Grouping

Cell = str | float | int | None


@dataclass(frozen=True, slots=True)
class Series:
    name: str
    values: tuple[float | None, ...]


@dataclass(frozen=True, slots=True)
class ChartData:
    categories: tuple[str, ...]
    series: tuple[Series, ...]


def parse(state: ChartState) -> ChartData:
    """Extract categories and series from ``state``.

    Trailing empty rows and columns are dropped; empty cells inside the data stay ``None`` so the
    chart shows a gap. Text in a value cell counts as empty. Series without a name are called
    "Series <row>".
    """
    rows = len(state.cells)
    width = len(state.cells[0]) if rows else 0
    if rows < 2 or width < 2:
        return ChartData((), ())

    used_rows = [r for r in range(1, rows) if _row_used(state, r)]
    used_cols = [c for c in range(1, width) if _column_used(state, c)]
    if not used_rows or not used_cols:
        return ChartData((), ())
    last_row, last_col = used_rows[-1], used_cols[-1]

    categories = tuple(state.cells[0][c].strip() for c in range(1, last_col + 1))
    series = tuple(
        Series(
            name=state.cells[r][0].strip() or f"Series {r}",
            values=tuple(state.values[r][c] for c in range(1, last_col + 1)),
        )
        for r in range(1, last_row + 1)
    )
    return ChartData(categories, series)


def _row_used(state: ChartState, r: int) -> bool:
    return bool(state.cells[r][0].strip()) or any(v is not None for v in state.values[r][1:])


def _column_used(state: ChartState, c: int) -> bool:
    return bool(state.cells[0][c].strip()) or any(row[c] is not None for row in state.values[1:])


def state_from_table(
    kind: ChartKind, grouping: Grouping, table: Sequence[Sequence[Cell]]
) -> ChartState:
    """Build a state from plain Python cells (numbers, text, ``None``), without any formulas.

    For sample data and tests; real charts get their state from the Calc data sheet.
    """
    cells = tuple(tuple(_raw(cell) for cell in row) for row in table)
    values = tuple(
        tuple(None if isinstance(cell, str) or cell is None else float(cell) for cell in row)
        for row in table
    )
    return ChartState(kind=kind, grouping=grouping, cells=cells, values=values)


def sample_state() -> ChartState:
    """Three products over three years: what a newly inserted chart shows."""
    return state_from_table(
        "column",
        "stacked",
        [
            [None, "2023", "2024", "2025"],
            ["Product A", 10, 12, 15],
            ["Product B", 20, 22, 21],
            ["Product C", 5, 8, 9],
        ],
    )


def _raw(cell: Cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, str):
        return cell
    number = float(cell)
    return str(int(number)) if number.is_integer() else repr(number)
