"""Bullet chart data sheet (M24).

Fixed columns like the scatter and Gantt sheets: ``Label | Actual | Target | Max`` and an optional
``Qualitative max``. The first row is the header. A row without an actual value is skipped; a
negative value or a missing maximum is a data-sheet error, reported as a message key.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.model import ChartState


@dataclass(frozen=True, slots=True)
class BulletRow:
    label: str
    actual: float
    target: float | None
    maximum: float
    qualitative: float | None = None


@dataclass(frozen=True, slots=True)
class BulletData:
    rows: tuple[BulletRow, ...]


class BulletError(ValueError):
    """The bullet data sheet is malformed; ``key`` names the message."""

    def __init__(self, key: str = "bullet_invalid") -> None:
        super().__init__(key)
        self.key = key


def parse(state: ChartState) -> BulletData:
    """Read the fixed columns of a bullet chart."""
    rows: list[BulletRow] = []
    for cells, values in zip(state.cells[1:], state.values[1:], strict=False):
        if not cells or not cells[0].strip():
            continue
        numbers = list(values[1:5])
        if not numbers or numbers[0] is None:
            continue
        actual = numbers[0]
        target = numbers[1] if len(numbers) > 1 else None
        maximum = numbers[2] if len(numbers) > 2 else None
        qualitative = numbers[3] if len(numbers) > 3 else None
        if maximum is None:
            raise BulletError("bullet_missing")
        if actual < 0 or maximum <= 0:
            raise BulletError("bullet_negative")
        rows.append(BulletRow(cells[0], actual, target, maximum, qualitative))
    if not rows:
        raise BulletError("bullet_empty")
    return BulletData(tuple(rows))
