"""Table cells: typed markers, numbers and text (M25).

A table is a chart kind whose data sheet is the cell grid. A cell may carry a typed marker:
``{harvey:75}``, ``{check:tick}``, ``{check:cross}``, ``{check:empty}`` or ``{spark:1,3,2,5}``.
Everything else is text, or a number when Calc evaluated it. A literal string starting with ``{``
is escaped as ``{{``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from librecharts.core.model import ChartState, TableSpec

CellKind = Literal["text", "number", "harvey", "check", "spark", "empty"]


@dataclass(frozen=True, slots=True)
class Cell:
    kind: CellKind
    text: str = ""
    number: float | None = None
    check: str = ""
    spark: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class TableData:
    cells: tuple[tuple[Cell, ...], ...]
    spec: TableSpec


def parse(state: ChartState) -> TableData:
    """Read every cell, evaluating typed markers and keeping Calc's numbers."""
    rows: list[tuple[Cell, ...]] = []
    for cells, values in zip(state.cells, state.values, strict=True):
        row: list[Cell] = []
        for text, number in zip(cells, values, strict=True):
            row.append(_cell(text, number))
        rows.append(tuple(row))
    return TableData(tuple(rows), state.table or TableSpec())


def _cell(text: str, number: float | None) -> Cell:
    if text.startswith("{{"):
        return Cell("text", text[1:])
    if text.startswith("{") and text.endswith("}"):
        body = text[1:-1]
        kind, _, argument = body.partition(":")
        if kind == "harvey":
            try:
                level = int(argument)
            except ValueError as exc:
                raise ValueError(f"invalid Harvey ball marker: {text!r}") from exc
            if level not in (0, 25, 50, 75, 100):
                raise ValueError(f"invalid Harvey ball level: {text!r}")
            return Cell("harvey", number=float(level))
        if kind == "check":
            if argument not in ("tick", "cross", "empty"):
                raise ValueError(f"invalid check marker: {text!r}")
            return Cell("check", check=argument)
        if kind == "spark":
            try:
                points = tuple(float(part) for part in argument.split(",") if part.strip())
            except ValueError as exc:
                raise ValueError(f"invalid sparkline marker: {text!r}") from exc
            return Cell("spark", spark=points)
        raise ValueError(f"unknown cell marker: {text!r}")
    if number is not None:
        return Cell("number", number=number)
    return Cell("empty" if not text else "text", text=text)


def column_widths(spec: TableSpec, columns: int) -> tuple[float, ...]:
    """Relative column widths, normalised to ``columns`` entries (equal when unspecified)."""
    if columns <= 0:
        return ()
    if not spec.widths:
        return tuple(1.0 / columns for _ in range(columns))
    widths = list(spec.widths[:columns])
    widths.extend([widths[-1] if widths else 1.0] * (columns - len(widths)))
    total = sum(widths)
    return tuple(width / total for width in widths)


def heatmap_range(data: TableData) -> tuple[float, float]:
    """The smallest and largest numeric cell; ``(0, 0)`` when there is none."""
    numbers = [
        cell.number
        for row in data.cells
        for cell in row
        if cell.kind == "number" and cell.number is not None
    ]
    return (min(numbers), max(numbers)) if numbers else (0.0, 0.0)
