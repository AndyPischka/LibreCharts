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
from datetime import date

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


def ranged(state: ChartState) -> tuple[ChartData, tuple[tuple[float | None, ...], ...]]:
    """The data of a floating-bar chart: the to values as series, the from levels beside them.

    Series rows come in pairs: data row 1 is the from level and row 2 the to level of the first
    floating bar, rows 3 and 4 the second, and so on; the bar's name comes from the from row. A
    pair whose both rows are empty is dropped; a dangling unpaired last row stays stored and
    unused, like any dangling index after a data edit. An empty from cell means the baseline.
    """
    paired = _paired_rows(state)
    if paired is None:
        return ChartData((), ()), ()
    categories, pairs = paired
    series = tuple(
        Series(name, tuple(state.values[lower][c] for c in range(1, len(categories) + 1)))
        for name, _upper, lower in pairs
    )
    bases = tuple(
        tuple(state.values[upper][c] for c in range(1, len(categories) + 1))
        for _name, upper, _lower in pairs
    )
    return ChartData(categories, series), bases


def errored(state: ChartState) -> tuple[ChartData, tuple[tuple[float | None, ...], ...]]:
    """The data of a chart with error bars: the series values and the error magnitudes beside them.

    Series rows come in pairs like in floating bars: the series value in an odd data row, its
    absolute error magnitude (±) in the row below it. An empty error cell means no whisker for that
    point; a pair whose both rows are empty is dropped, and a dangling unpaired last row stays
    stored and unused.
    """
    paired = _paired_rows(state)
    if paired is None:
        return ChartData((), ()), ()
    categories, pairs = paired
    series = tuple(
        Series(name, tuple(state.values[upper][c] for c in range(1, len(categories) + 1)))
        for name, upper, _lower in pairs
    )
    errs = tuple(
        tuple(state.values[lower][c] for c in range(1, len(categories) + 1))
        for _name, _upper, lower in pairs
    )
    return ChartData(categories, series), errs


def _paired_rows(
    state: ChartState,
) -> tuple[tuple[str, ...], tuple[tuple[str, int, int], ...]] | None:
    """The categories and the paired series rows of a data sheet whose rows come two by two.

    Each pair is (name, upper row, lower row), the name from the upper row; rows start at 1, so
    the upper row is odd. A pair whose both rows are empty is dropped, a dangling unpaired last
    row stays stored and unused.
    """
    rows = len(state.cells)
    width = len(state.cells[0]) if rows else 0
    if rows < 2 or width < 2:
        return None
    used_cols = [c for c in range(1, width) if _column_used(state, c)]
    if not used_cols:
        return None
    last_col = used_cols[-1]
    categories = tuple(state.cells[0][c].strip() for c in range(1, last_col + 1))
    pairs: list[tuple[str, int, int]] = []
    for r in range(1, rows - 1, 2):
        if not (_row_used(state, r) or _row_used(state, r + 1)):
            continue
        pairs.append((state.cells[r][0].strip() or f"Series {r}", r, r + 1))
    return categories, tuple(pairs)


def with_error_margins(data: ChartData, errors: tuple[tuple[float | None, ...], ...]) -> ChartData:
    """``data`` extended by two margin series per errored series, at value ± error.

    The scale of a chart with error bars covers value ± error (M15); the added series hold the
    upper and lower margin of every series that has an error row. Series without error data keep
    ``data`` as it is.
    """
    margins: list[Series] = []
    for i, series in enumerate(data.series):
        err = errors[i] if i < len(errors) else None
        if err is None:
            continue
        margins.append(
            Series(
                f"{series.name} +",
                tuple(
                    None if v is None or e is None else v + e
                    for v, e in zip(series.values, err, strict=True)
                ),
            )
        )
        margins.append(
            Series(
                f"{series.name} -",
                tuple(
                    None if v is None or e is None else v - e
                    for v, e in zip(series.values, err, strict=True)
                ),
            )
        )
    if not margins:
        return data
    return ChartData(data.categories, (*data.series, *margins))


def with_from_levels(data: ChartData, bases: tuple[tuple[float | None, ...], ...]) -> ChartData:
    """``data`` extended by one series per floating bar, at its from level.

    The scale of a floating-bar chart covers the from levels as well (M15).
    """
    return ChartData(
        data.categories,
        (*data.series, *(Series(f"From {i}", base) for i, base in enumerate(bases))),
    )


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
        values=tuple(tuple(as_number(result) for result in row) for row in results),
    )


def as_number(result: object) -> float | None:
    """A cell result from ``getDataArray`` as a finite number, else ``None``."""
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
    return _sample_years("line", "Revenue", "Costs")


def sample_area_state() -> ChartState:
    """Two products over six years: what a new area chart shows.

    Areas stack, so the series must be parts of a whole; revenue and costs would sum to a number
    nobody reads.
    """
    return _sample_years("area", "Product A", "Product B")


def sample_pie_state() -> ChartState:
    """Revenue shares by product in two years: what a new pie chart shows (one pie per year)."""
    return state_from_table(
        "pie",
        "stacked",
        [
            [None, "2024", "2025"],
            ["Product A", 40, 35],
            ["Product B", 35, 38],
            ["Product C", 25, 27],
        ],
    )


def sample_scatter_state() -> ChartState:
    """Eight points in two groups: what a new scatter chart shows.

    The size column stays empty; any number in it turns a point into a bubble.
    """
    return state_from_table(
        "scatter",
        "stacked",
        [
            ["Label", "X", "Y", "Size", "Group"],
            ["Alpha", 12, 30, None, "Group 1"],
            ["Beta", 18, 42, None, "Group 1"],
            ["Gamma", 25, 38, None, "Group 1"],
            ["Delta", 31, 55, None, "Group 1"],
            ["Epsilon", 14, 18, None, "Group 2"],
            ["Zeta", 22, 25, None, "Group 2"],
            ["Eta", 35, 33, None, "Group 2"],
            ["Theta", 40, 48, None, "Group 2"],
        ],
    )


def sample_butterfly_state() -> ChartState:
    """Population by age group: what a new butterfly chart shows (men left, women right)."""
    return state_from_table(
        "butterfly",
        "stacked",
        [
            [None, "0-14", "15-29", "30-44", "45-59", "60+"],
            ["Men", 6.5, 8.1, 9.4, 8.7, 8.2],
            ["Women", 6.2, 7.8, 9.3, 8.9, 10.1],
        ],
    )


def sample_gantt_state() -> ChartState:
    """A project of two phases, five activities and two milestones over half a year: what a new
    Gantt chart shows. Dates are Calc serial numbers (``core/gantt.py``). *Testing* has two bars,
    to show that one row can carry several (M17)."""

    def day(month: int, number: int) -> int:
        return (date(2026, month, number) - date(1899, 12, 30)).days

    return state_from_table(
        "gantt",
        "stacked",
        [
            ["Activity", "Start", "End", "Remark", "Phase", "Start", "End"],
            ["Concept", day(1, 5), day(2, 27), None, "x", None, None],
            ["Requirements", day(1, 5), day(1, 30), "Team A", None, None, None],
            ["Design", day(2, 2), day(2, 27), None, None, None, None],
            ["Design approved", day(2, 27), None, None, None, None, None],
            ["Implementation", day(3, 2), day(6, 30), None, "x", None, None],
            ["Development", day(3, 2), day(5, 15), "Team B", None, None, None],
            ["Testing", day(4, 13), day(5, 15), None, None, day(5, 25), day(6, 12)],
            ["Rollout", day(6, 1), day(6, 26), None, None, None, None],
            ["Go-live", day(6, 30), None, None, None, None, None],
        ],
    )


def _sample_years(kind: ChartKind, first: str, second: str) -> ChartState:
    return state_from_table(
        kind,
        "stacked",
        [
            [None, "2020", "2021", "2022", "2023", "2024", "2025"],
            [first, 12, 15, 18, 22, 27, 33],
            [second, 9, 10, 12, 14, 16, 19],
        ],
    )


def _raw(cell: Cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, str):
        return cell
    return number_text(float(cell))


def number_text(number: float) -> str:
    """A number as cell content: ``12`` for whole numbers, else Python's shortest exact form."""
    return str(int(number)) if number.is_integer() else repr(number)
