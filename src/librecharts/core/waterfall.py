"""Data sheet conventions for waterfall charts: steps, subtotals and the running total.

Data sheet layout (rows are fixed, unlike the series rows of column and bar charts):

- row 1: category names, one per column;
- row 2: the values; a step adds this *change* to the running total;
- row 3: marks a column as a *total* (any entry except empty, 0, false, no, nein, n).

A total column is drawn from zero up to the running total. An empty value cell shows the running
total so far; a given value replaces it, and the running total continues from there. An empty
value cell of an ordinary step is a gap: it changes nothing and has no label.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.datasheet import ChartData, Series
from librecharts.core.model import ChartState

_NOT_A_MARK = frozenset({"", "0", "false", "no", "nein", "n"})


@dataclass(frozen=True, slots=True)
class Step:
    """One column of a waterfall: a change (start -> end) or a total (0 -> end).

    ``segments`` is empty for a single running total; a stacked waterfall (M15) fills it with one
    (start, end, has_value) triple per series row of the data sheet.
    """

    name: str
    start: float
    end: float
    is_total: bool
    has_value: bool  # False for the gap of an ordinary step
    segments: tuple[tuple[float, float, bool], ...] = ()

    @property
    def change(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class WaterfallData:
    steps: tuple[Step, ...]
    stacked: bool = False


def levels(data: WaterfallData) -> ChartData:
    """The levels the columns end at, as data for annotations: one value per step.

    A difference or CAGR arrow on a waterfall chart measures these (the running total after a
    step, or the value of a total).
    """
    names = tuple(step.name for step in data.steps)
    return ChartData(names, (Series("Level", tuple(step.end for step in data.steps)),))


def floor(data: WaterfallData) -> float:
    """The lowest level any step (not a total) touches; 0 if there are none.

    Totals stand on the baseline, so only the range below this level can be cut out of the
    scale without touching a step.
    """
    touched = [
        level for step in data.steps if not step.is_total for level in (step.start, step.end)
    ]
    return min(touched, default=0.0)


def parse_waterfall(state: ChartState) -> WaterfallData:
    """Extract the steps from the data sheet of ``state``; empty if there is nothing to draw.

    With ``state.stacked`` the value rows are row 1 and every used row from row 3 down (row 2 stays
    the total-mark row): each value row is one series whose changes stack in the column, each from
    its own running total. A total column is drawn as one segment from zero to the total.
    """
    rows = len(state.cells)
    width = len(state.cells[0]) if rows else 0
    if rows < 2 or width < 2:
        return WaterfallData(())

    def is_total(c: int) -> bool:
        return rows > 2 and state.cells[2][c].strip().lower() not in _NOT_A_MARK

    def used(c: int) -> bool:
        return (
            bool(state.cells[0][c].strip())
            or any(state.values[r][c] is not None for r in value_rows)
            or is_total(c)
        )

    value_rows = [1] + [r for r in range(3, rows) if _row_used(state, r)] if state.stacked else [1]
    columns = [c for c in range(1, width) if used(c)]
    if not columns:
        return WaterfallData(())

    steps: list[Step] = []
    running = 0.0
    for c in range(1, columns[-1] + 1):
        name = state.cells[0][c].strip()
        if is_total(c):
            value = state.values[1][c]
            end = running if value is None else value
            running = end
            segments = ((0.0, end, True),) if state.stacked else ()
            steps.append(Step(name, 0.0, end, True, True, segments))
        elif not state.stacked:
            value = state.values[1][c]
            end = running + (value or 0.0)
            steps.append(Step(name, running, end, False, value is not None))
            running = end
        else:  # stacked: the series rows stack their changes in one running total
            built: list[tuple[float, float, bool]] = []
            for r in value_rows:
                value = state.values[r][c]
                end = running + (value or 0.0)
                built.append((running, end, value is not None))
                running = end
            segments = tuple(built)
            steps.append(
                Step(
                    name,
                    segments[0][0],
                    segments[-1][1],
                    False,
                    any(has for _, _, has in segments),
                    segments,
                )
            )
    return WaterfallData(tuple(steps), state.stacked)


def _row_used(state: ChartState, r: int) -> bool:
    return bool(state.cells[r][0].strip()) or any(v is not None for v in state.values[r][1:])
