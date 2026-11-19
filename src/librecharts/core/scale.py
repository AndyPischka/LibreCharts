"""Axis scaling: pick a "nice" step and round the value range to multiples of it (M6, M23)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

AxisKind = Literal["linear", "log"]


@dataclass(frozen=True, slots=True)
class Axis:
    """A value axis from ``minimum`` to ``maximum`` in steps of ``step``.

    ``scale`` is ``"linear"`` or ``"log"``. :meth:`fraction` maps a value to 0 at the minimum and
    1 at the maximum, so layouts that support a logarithmic axis need no formula of their own.
    """

    minimum: float
    maximum: float
    step: float
    scale: AxisKind = "linear"

    def __post_init__(self) -> None:
        if self.scale not in ("linear", "log"):
            raise ValueError(f"unknown axis scale: {self.scale!r}")
        if self.scale == "log" and self.minimum <= 0:
            raise ValueError("a logarithmic axis needs a positive minimum")

    def ticks(self) -> list[float]:
        if self.scale == "log":
            return _log_ticks(self.minimum, self.maximum)
        count = round((self.maximum - self.minimum) / self.step)
        return [round(self.minimum + i * self.step, 12) for i in range(count + 1)]

    def fraction(self, value: float) -> float:
        """Where ``value`` sits on the axis: 0 at the minimum, 1 at the maximum."""
        if self.scale == "log":
            span = math.log10(self.maximum) - math.log10(self.minimum)
            return (math.log10(value) - math.log10(self.minimum)) / span if span else 0.0
        span = self.maximum - self.minimum
        return (value - self.minimum) / span if span else 0.0


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


def manual_axis(
    low: float | None,
    high: float | None,
    step: float | None = None,
    *,
    scale: AxisKind = "linear",
    fallback: Axis | None = None,
) -> Axis:
    """An axis from the user's limits, filling a missing bound and step from ``fallback``.

    At least one of ``low`` and ``high`` is needed. A missing bound is rounded outwards to the
    step; a missing step uses the fallback's step (or a nice one). Raises ``ValueError`` for an
    invalid range or a logarithmic axis with a non-positive bound.
    """
    if low is None and high is None:
        return fallback if fallback is not None else nice_axis(0.0, 0.0)
    if step is None:
        step = (
            fallback.step
            if fallback is not None
            else _nice_step(
                ((high if high is not None else 0.0) - (low if low is not None else 0.0)) / 5 or 1.0
            )
        )
    if step <= 0 or not math.isfinite(step):
        raise ValueError("the axis step must be positive and finite")
    if scale == "log":
        low = low if low is not None else (fallback.minimum if fallback else 1.0)
        high = high if high is not None else (fallback.maximum if fallback else low * 10)
        if low <= 0 or high <= 0:
            raise ValueError("a logarithmic axis needs positive bounds")
        if low >= high:
            raise ValueError("the axis minimum must be below its maximum")
        return Axis(low, high, step, "log")
    if low is not None and high is not None:
        if low >= high:
            raise ValueError("the axis minimum must be below its maximum")
        return Axis(low, high, step)
    if low is None:
        if fallback is not None:
            base = fallback.minimum
        elif high is not None:
            base = high - 5 * step
        else:  # unreachable: both None returned above
            base = 0.0
        low = math.floor(round(base / step, 9)) * step
    if high is None:
        base = fallback.maximum if fallback is not None else low + 5 * step
        high = math.ceil(round(base / step, 9)) * step
    if low >= high:
        high = low + step
    return Axis(round(low, 12), round(high, 12), step)


def _log_ticks(low: float, high: float) -> list[float]:
    """Powers of ten and their 2 and 5 multiples inside ``[low, high]``."""
    if low <= 0 or high <= 0 or low >= high:
        return []
    first = math.floor(math.log10(low))
    last = math.ceil(math.log10(high))
    out: list[float] = []
    for exponent in range(first, last + 1):
        for factor in (1, 2, 5):
            value = factor * 10.0**exponent
            if low - 1e-12 <= value <= high + 1e-12:
                out.append(round(value, 12))
    return out
