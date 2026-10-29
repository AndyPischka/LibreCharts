"""Data sheet conventions: turn a table of cells into chart data (and back for sample data).

Layout, like think-cell: the first row holds category names, the first column holds series names,
the top-left cell is unused. Every following row is one series, every following column one category.

Category and series names are taken from the raw cell contents, so a formula in a header cell
shows up as its text. Only the value grid is evaluated by Calc.
"""

from __future__ import annotations

import math
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
    kind: ChartKind, grouping: Grouping, table: Sequence[Sequence[Cell]], percent: bool = False
) -> ChartState:
    """Build a state from plain Python cells (numbers, text, ``None``), without any formulas.

    For sample data and tests; real charts get their state from the Calc data sheet.
    """
    cells = tuple(tuple(_raw(cell) for cell in row) for row in table)
    values = tuple(
        tuple(None if isinstance(cell, str) or cell is None else float(cell) for cell in row)
        for row in table
    )
    return ChartState(kind=kind, grouping=grouping, cells=cells, values=values, percent=percent)


def state_from_sheet(
    kind: ChartKind,
    grouping: Grouping,
    formulas: Sequence[Sequence[str]],
    results: Sequence[Sequence[object]],
) -> ChartState:
    """Build a state from a Calc range read with ``getFormulaArray`` and ``getDataArray``.

    ``formulas`` are the raw contents (numbers, text, ``=...``), ``results`` what Calc computed:
    floats for numbers, strings for text and empty cells. Non-numbers become ``None``.
    """
    return ChartState(
        kind=kind,
        grouping=grouping,
        cells=tuple(tuple(str(cell) for cell in row) for row in formulas),
        values=tuple(tuple(_number(result) for result in row) for row in results),
    )


def _number(result: object) -> float | None:
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        return None
    return float(result) if math.isfinite(result) else None


def sample_waterfall_state() -> ChartState:
    """A bridge from a start value to an end value: what a new waterfall chart shows.

    ``grouping`` has no meaning for waterfalls and stays "stacked".
    """
    return state_from_table(
        "waterfall",
        "stacked",
        [
            [None, "Start", "Growth", "New markets", "Costs", "Currency", "End"],
            ["Value", 100, 30, 15, -25, -10, None],
            ["Total", "x", None, None, None, None, "x"],
        ],
    )


def sample_mekko_state() -> ChartState:
    """Market sizes by region and product: what a new Mekko chart shows (a percent Mekko whose
    widths are the column sums)."""
    return state_from_table(
        "mekko",
        "stacked",
        [
            [None, "Europe", "Americas", "Asia", "Other"],
            ["Product A", 40, 30, 20, 4],
            ["Product B", 25, 45, 40, 3],
            ["Product C", 15, 10, 30, 3],
        ],
        percent=True,
    )


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


def sample_line_state() -> ChartState:
    """Revenue and costs over six years: what a new line chart shows."""
    return _sample_years("line")


def sample_area_state() -> ChartState:
    """Revenue and costs over six years: what a new area chart shows."""
    return _sample_years("area")


def _sample_years(kind: ChartKind) -> ChartState:
    return state_from_table(
        kind,
        "stacked",
        [
            [None, "2020", "2021", "2022", "2023", "2024", "2025"],
            ["Revenue", 12, 15, 18, 22, 27, 33],
            ["Costs", 9, 10, 12, 14, 16, 19],
        ],
    )


def _raw(cell: Cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, str):
        return cell
    number = float(cell)
    return str(int(number)) if number.is_integer() else repr(number)
