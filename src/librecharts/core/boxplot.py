"""Box plot data sheet (M24): one five-number summary per category.

Fixed columns ``Label | Min | Q1 | Median | Q3 | Max`` and optional outlier values after them.
The first row is the header. The summary must be ordered; violations are reported as a message key.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.model import ChartState


@dataclass(frozen=True, slots=True)
class BoxRow:
    label: str
    minimum: float
    q1: float
    median: float
    q3: float
    maximum: float
    outliers: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class BoxData:
    rows: tuple[BoxRow, ...]


class BoxError(ValueError):
    """The box plot data sheet is malformed; ``key`` names the message."""

    def __init__(self, key: str = "boxplot_invalid") -> None:
        super().__init__(key)
        self.key = key


def parse(state: ChartState) -> BoxData:
    """Read the five-number summaries of a box plot."""
    rows: list[BoxRow] = []
    for cells, values in zip(state.cells[1:], state.values[1:], strict=False):
        if not cells or not cells[0].strip() or values[1] is None:
            continue
        numbers = [*values[1:6]]
        if any(value is None for value in numbers):
            raise BoxError("boxplot_incomplete")
        minimum, q1, median, q3, maximum = (float(value) for value in numbers if value is not None)
        if not minimum <= q1 <= median <= q3 <= maximum:
            raise BoxError("boxplot_order")
        outliers = tuple(value for value in values[6:] if value is not None)
        rows.append(BoxRow(cells[0], minimum, q1, median, q3, maximum, outliers))
    if not rows:
        raise BoxError("boxplot_empty")
    return BoxData(tuple(rows))
