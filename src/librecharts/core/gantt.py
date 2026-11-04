"""Data sheet conventions for Gantt charts: one row per activity, fixed columns (M10, M17).

Data sheet layout (columns are read by position, the header row only names them for the user):

- column A: the label of the row;
- column B: the start date; column C: the end date (both included);
- column D: a remark (optional text), shown next to the bar;
- column E: the phase marker (optional): any text makes the row a phase, a bracket over the rows
  that follow it, like the waterfall's "Total" marker;
- columns F/G, H/I, ...: further start/end pairs, one more bar each (M17).

Dates are Calc serial numbers (days since 1899-12-30), as ``getDataArray`` returns them; the time
of day is ignored. The row type follows from the cells: the first pair (B/C) gives a bar, a
milestone (a single date or start equal to end) or, with a phase marker, a phase; no dates at all
give a heading. Further pairs are bars: both dates are required, a single date is ignored, and
start equal to end is a one-day bar. Completely empty rows are skipped. Bars and milestones take
the colour of the phase above them (phases are numbered from 0 in order; rows before the first
phase use colour 0).
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
class Mark:
    """One bar or milestone of a row; a milestone's ``end`` equals its ``start``."""

    start: date
    end: date  # inclusive
    kind: Literal["bar", "milestone"]


@dataclass(frozen=True, slots=True)
class Row:
    label: str
    kind: RowKind
    start: date | None  # the earliest start of the row's marks; None only for a heading
    end: date | None  # the latest end (inclusive); None only for a heading
    remark: str
    color: int  # palette index: the number of the phase the row belongs to
    marks: tuple[Mark, ...] = ()  # the bars and milestones, in data sheet order


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


def pairs(width: int) -> tuple[tuple[int, int], ...]:
    """The start/end column pairs of a data sheet ``width`` columns wide.

    The first pair is ``(START, END)``; further pairs follow the phase column two by two
    (F/G, H/I, ...), so that a row can have several bars (M17).
    """
    found = [(START, END)]
    column = PHASE + 1
    while column + 1 < width:
        found.append((column, column + 1))
        column += 2
    return tuple(found)


def parse_gantt(state: ChartState, sort: SortOrder = "none") -> GanttData:
    """The rows of ``state``'s data sheet; ``sort="ascending"`` orders them by start date.

    Sorting keeps phases and headings in place and sorts the rows between them. A row with several
    bars sorts by its earliest start.
    """
    count = len(state.cells)
    width = len(state.cells[0]) if count else 0
    column_pairs = pairs(width)
    phases: list[str] = []
    rows: list[Row] = []
    for r in range(1, count):
        cells, values = state.cells[r], state.values[r]
        label, remark, marker = (cells[c].strip() if width > c else "" for c in (0, REMARK, PHASE))
        marks = _marks(values, column_pairs)
        if not marks:
            if not label and not remark:
                continue
            rows.append(Row(label, "heading", None, None, remark, max(len(phases) - 1, 0)))
            continue
        kind: RowKind
        if marker:
            kind = "phase"
            phases.append(label)
        elif len(marks) == 1 and marks[0].kind == "milestone":
            kind = "milestone"
        else:
            kind = "bar"
        rows.append(
            Row(
                label,
                kind,
                min(mark.start for mark in marks),
                max(mark.end for mark in marks),
                remark,
                max(len(phases) - 1, 0),
                marks,
            )
        )
    if sort == "ascending":
        rows = _sorted(rows)
    return GanttData(tuple(rows), tuple(phases))


def _marks(
    values: tuple[float | None, ...], column_pairs: tuple[tuple[int, int], ...]
) -> tuple[Mark, ...]:
    """The bars and milestones of one row, in data sheet order."""
    marks: list[Mark] = []
    start, end = _pair(values, *column_pairs[0])
    if start is None and end is not None:  # an end date alone is a milestone
        start = end
    elif end is None and start is not None:  # a start date alone is a milestone
        end = start
    if start is not None and end is not None:
        marks.append(Mark(start, end, "milestone" if end == start else "bar"))
    for start_column, end_column in column_pairs[1:]:
        start, end = _pair(values, start_column, end_column)
        if start is None or end is None:  # a further pair is a bar: it needs both dates
            continue
        marks.append(Mark(start, end, "bar"))
    return tuple(marks)


def _pair(
    values: tuple[float | None, ...], start_column: int, end_column: int
) -> tuple[date | None, date | None]:
    """The two dates of one column pair, in order; both ``None`` if both cells are empty."""
    start_value, end_value = values[start_column], values[end_column]
    start = None if start_value is None else to_date(start_value)
    end = None if end_value is None else to_date(end_value)
    if start is not None and end is not None and end < start:
        start, end = end, start
    return start, end


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
