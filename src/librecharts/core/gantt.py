"""Data sheet conventions for Gantt charts: one row per activity, fixed columns (M10).

Data sheet layout (columns are read by position, the header row only names them for the user):

- column A: the label of the row;
- column B: the start date; column C: the end date (both included);
- column D: a remark (optional text), shown next to the bar;
- column E: the phase marker (optional): any text makes the row a phase, a bracket over the rows
  that follow it, like the waterfall's "Total" marker.

Dates are Calc serial numbers (days since 1899-12-30), as ``getDataArray`` returns them; the time
of day is ignored. The row type follows from the cells: start and end give a bar, a single date (or
start equal to end) a milestone, a phase marker with dates a phase, no dates at all a heading.
Completely empty rows are skipped. Bars and milestones take the colour of the phase above them
(phases are numbered from 0 in order; rows before the first phase use colour 0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from librecharts.core.datasheet import ChartData, Series
from librecharts.core.model import ChartState, SortOrder

START, END, REMARK, PHASE = 1, 2, 3, 4  # column indices
EPOCH = date(1899, 12, 30)  # Calc's default null date: serial number 0
MIN_YEAR, MAX_YEAR = 1000, 9000  # dates outside count as empty; keeps the scale arithmetic safe

RowKind = Literal["bar", "milestone", "phase", "heading"]


@dataclass(frozen=True, slots=True)
class Row:
    label: str
    kind: RowKind
    start: date | None  # None only for a heading
    end: date | None  # inclusive; equal to start for a milestone
    remark: str
    color: int  # palette index: the number of the phase the row belongs to


@dataclass(frozen=True, slots=True)
class GanttData:
    rows: tuple[Row, ...]
    phases: tuple[str, ...]  # phase labels in order; index = colour

    @property
    def dated(self) -> tuple[Row, ...]:
        return tuple(row for row in self.rows if row.start is not None)


def to_date(serial: float) -> date | None:
    """The day of a Calc serial number; ``None`` outside the supported years."""
    try:
        day = EPOCH + timedelta(days=math.floor(serial))
    except OverflowError:
        return None
    return day if MIN_YEAR <= day.year <= MAX_YEAR else None


def serial(day: date) -> int:
    """The Calc serial number of ``day``."""
    return (day - EPOCH).days


def parse_gantt(state: ChartState, sort: SortOrder = "none") -> GanttData:
    """The rows of ``state``'s data sheet; ``sort="ascending"`` orders them by start date.

    Sorting keeps phases and headings in place and sorts the rows between them.
    """
    count = len(state.cells)
    width = len(state.cells[0]) if count else 0
    phases: list[str] = []
    rows: list[Row] = []
    for r in range(1, count):
        cells, values = state.cells[r], state.values[r]
        label, remark, marker = (cells[c].strip() if width > c else "" for c in (0, REMARK, PHASE))
        start, end = (
            to_date(value) if width > c and (value := values[c]) is not None else None
            for c in (START, END)
        )
        if start is None:
            start = end
        if start is not None and end is not None and end < start:
            start, end = end, start
        kind: RowKind
        if start is None:
            if not label and not remark:
                continue
            kind = "heading"
        elif marker:
            kind = "phase"
            phases.append(label)
        elif end is None or end == start:
            kind, end = "milestone", start
        else:
            kind = "bar"
        rows.append(Row(label, kind, start, end, remark, max(len(phases) - 1, 0)))
    if sort == "ascending":
        rows = _sorted(rows)
    return GanttData(tuple(rows), tuple(phases))


def _sorted(rows: list[Row]) -> list[Row]:
    """Bars and milestones by start date within each block between phases and headings."""
    out: list[Row] = []
    block: list[Row] = []
    for row in rows:
        if row.kind in ("phase", "heading"):
            out.extend(sorted(block, key=_start))
            out.append(row)
            block = []
        else:
            block.append(row)
    out.extend(sorted(block, key=_start))
    return out


def _start(row: Row) -> date:
    return row.start or date.min


def starts(data: GanttData) -> ChartData:
    """The rows as chart data, for annotations: one category per row, the start serials.

    A date line is a value line whose value is a serial number.
    """
    return ChartData(
        tuple(row.label for row in data.rows),
        (
            Series(
                "Start",
                tuple(None if row.start is None else float(serial(row.start)) for row in data.rows),
            ),
        ),
    )
