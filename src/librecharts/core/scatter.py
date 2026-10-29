"""Data sheet conventions for scatter and bubble charts: one row per point, fixed columns.

Data sheet layout (columns are read by position, the header row only names them for the user):

- column A: the label of the point (optional, shown right of the point);
- column B: x; column C: y; a row with an empty or non-numeric x or y is skipped;
- column D: the size (optional); a point with a positive size is drawn as a bubble whose area is
  proportional to the size, a point without one as a plain marker;
- column E: the group (optional text); points of one group share a colour and a legend entry.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.datasheet import ChartData, Series
from librecharts.core.model import ChartState

X, Y, SIZE, GROUP = 1, 2, 3, 4  # column indices


@dataclass(frozen=True, slots=True)
class Point:
    label: str
    x: float
    y: float
    size: float | None  # None: a marker; else a bubble
    group: int  # index into ScatterData.groups, selects the colour


@dataclass(frozen=True, slots=True)
class ScatterData:
    points: tuple[Point, ...]
    groups: tuple[str, ...]  # group names in order of first appearance; "" for no group

    @property
    def bubbles(self) -> bool:
        """Whether any point has a size (a bubble chart)."""
        return any(point.size is not None for point in self.points)


def parse_scatter(state: ChartState) -> ScatterData:
    """The points of ``state``'s data sheet; empty if there is nothing to draw."""
    rows = len(state.cells)
    width = len(state.cells[0]) if rows else 0
    if rows < 2 or width <= Y:
        return ScatterData((), ())
    groups: list[str] = []
    points: list[Point] = []
    for r in range(1, rows):
        x, y = state.values[r][X], state.values[r][Y]
        if x is None or y is None:
            continue
        size = state.values[r][SIZE] if width > SIZE else None
        name = state.cells[r][GROUP].strip() if width > GROUP else ""
        if name not in groups:
            groups.append(name)
        points.append(
            Point(
                state.cells[r][0].strip(),
                x,
                y,
                size if size is not None and size > 0 else None,
                groups.index(name),
            )
        )
    return ScatterData(tuple(points), tuple(groups))


def levels(data: ScatterData) -> ChartData:
    """The y values as chart data, for annotations: one category per point, one series.

    A value line on a scatter chart marks a y level; its average is the mean of the y values.
    """
    return ChartData(
        tuple(point.label for point in data.points),
        (Series("Y", tuple(point.y for point in data.points)),),
    )
