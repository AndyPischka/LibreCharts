"""Axis scaling: pick a "nice" step and round the value range to multiples of it."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Axis:
    """A value axis from ``minimum`` to ``maximum`` in steps of ``step``."""

    minimum: float
    maximum: float
    step: float

    def ticks(self) -> list[float]:
        count = round((self.maximum - self.minimum) / self.step)
        return [round(self.minimum + i * self.step, 12) for i in range(count + 1)]


def _nice_step(raw: float) -> float:
    exponent = math.floor(math.log10(raw))
    fraction = raw / 10.0**exponent
    return next((n for n in (1, 2, 5) if fraction <= n), 10) * 10.0**exponent


def nice_axis(low: float, high: float, max_ticks: int = 6, *, include_zero: bool = True) -> Axis:
    """Return an axis covering ``[low, high]`` with at most about ``max_ticks`` ticks.

    ``include_zero`` keeps the baseline visible, which column and bar charts need.
    """
    if not (math.isfinite(low) and math.isfinite(high)):
        raise ValueError("axis bounds must be finite")
    if low > high:
        raise ValueError("low must not exceed high")
    if max_ticks < 2:
        raise ValueError("max_ticks must be at least 2")

    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    if low == high:
        high = low + 1.0

    step = _nice_step((high - low) / (max_ticks - 1))
    # round(..., 9) absorbs float noise such as 0.3 / 0.1 == 2.9999999999999996
    minimum = math.floor(round(low / step, 9)) * step
    maximum = math.ceil(round(high / step, 9)) * step
    return Axis(round(minimum, 12), round(maximum, 12), step)
