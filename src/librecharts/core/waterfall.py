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

from librecharts.core.model import ChartState

_NOT_A_MARK = frozenset({"", "0", "false", "no", "nein", "n"})


@dataclass(frozen=True, slots=True)
class Step:
    """One column of a waterfall: a change (start -> end) or a total (0 -> end)."""

    name: str
    start: float
    end: float
    is_total: bool
    has_value: bool  # False for the gap of an ordinary step

    @property
    def change(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class WaterfallData:
    steps: tuple[Step, ...]


def parse_waterfall(state: ChartState) -> WaterfallData:
    """Extract the steps from the data sheet of ``state``; empty if there is nothing to draw."""
    rows = len(state.cells)
    width = len(state.cells[0]) if rows else 0
    if rows < 2 or width < 2:
        return WaterfallData(())

    def is_total(c: int) -> bool:
        return rows > 2 and state.cells[2][c].strip().lower() not in _NOT_A_MARK

    def used(c: int) -> bool:
        return bool(state.cells[0][c].strip()) or state.values[1][c] is not None or is_total(c)

    columns = [c for c in range(1, width) if used(c)]
    if not columns:
        return WaterfallData(())

    steps: list[Step] = []
    running = 0.0
    for c in range(1, columns[-1] + 1):
        name, value = state.cells[0][c].strip(), state.values[1][c]
        if is_total(c):
            end = running if value is None else value
            steps.append(Step(name, 0.0, end, True, True))
            running = end
        else:
            end = running + (value or 0.0)
            steps.append(Step(name, running, end, False, value is not None))
            running = end
    return WaterfallData(tuple(steps))
