"""Trendlines and forecasts (M23).

The layouts draw a fitted straight line through one series: a least-squares fit on the values
(``linear``) or on their logarithms (``exponential``). Empty cells are skipped. The module keeps
the maths pure, so the geometry is testable without LibreOffice; the layouts place the result.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from librecharts.core.model import TrendKind


@dataclass(frozen=True, slots=True)
class Fit:
    """A fitted trend ``y = a * exp(b x)`` (exponential) or ``y = a + b x`` (linear)."""

    a: float
    b: float
    r2: float
    kind: TrendKind

    def value(self, x: float) -> float:
        """The fitted value at ``x``."""
        if self.kind == "exponential":
            return self.a * math.exp(self.b * x)
        return self.a + self.b * x


def fit(points: list[tuple[float, float]], kind: TrendKind = "linear") -> Fit | None:
    """A least-squares fit through ``points``; ``None`` with fewer than two usable points."""
    if len(points) < 2:
        return None
    if kind == "exponential" and any(y <= 0 for _, y in points):
        raise ValueError("an exponential trend needs positive values")
    xs = [x for x, _ in points]
    ys = [math.log(y) if kind == "exponential" else y for _, y in points]
    count = len(xs)
    mean_x, mean_y = sum(xs) / count, sum(ys) / count
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = mean_y - slope * mean_x
    predicted = [intercept + slope * x for x in xs]
    residual = sum((y - p) ** 2 for y, p in zip(ys, predicted, strict=True))
    total = sum((y - mean_y) ** 2 for y in ys)
    r2 = 1.0 - residual / total if total else 1.0
    a = math.exp(intercept) if kind == "exponential" else intercept
    return Fit(a, slope, max(0.0, min(1.0, r2)), kind)


def label(fit: Fit, fmt: object | None = None, *, equation: bool = False) -> str:
    """The R² (and optional equation) as a short slide label, in the chart's separator."""
    r2 = _number(fit.r2)
    separator = getattr(fmt, "separator", ".")
    if separator == ",":
        r2 = r2.replace(".", ",")
    text = f"R² = {r2}"
    if equation:
        a = _number(abs(fit.a)).rstrip("0").rstrip(".")
        b = _number(abs(fit.b)).rstrip("0").rstrip(".")
        if separator == ",":
            a, b = a.replace(".", ","), b.replace(".", ",")
        sign = "-" if fit.b < 0 else "+"
        if fit.kind == "exponential":
            text += f"  y = {a}·e^({sign}{b}x)"
        else:
            text += f"  y = {a} {sign} {b}x"
    return text


def points_of(values: Sequence[float | None], *, offset: float = 0.0) -> list[tuple[float, float]]:
    """``(index + offset, value)`` for every value that is not empty."""
    return [(index + offset, value) for index, value in enumerate(values) if value is not None]


def _number(value: float) -> str:
    """Two decimals without trailing zeros, for R² and the equation."""
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"
