"""Consistent rounding: labels that add up to the rounded total (M16).

Where value labels are the parts of a shown total, rounding each label on its own makes them
drift apart from the total: ``33% + 33% + 33%`` next to a total of ``101%``. The functions here
round with the largest remainder method, in the number format's own scale and precision, so the
labels keep the look of ``format_value``/``format_share`` while their sum matches the rounded
total exactly.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from librecharts.core.layout.common import format_share, format_value
from librecharts.core.model import Format
from librecharts.core.percent import share


def consistent(values: Sequence[float | None], total: float, fmt: Format) -> tuple[str | None, ...]:
    """The segment labels of one column: rounded so they add up to the rounded ``total``.

    ``values`` are the segment values of one category (a ``None`` keeps its place without a
    label), ``total`` their sum as the total label shows it. Every value is scaled by the
    format's magnitude and rounded at the format's precision (the same default
    ``format_value`` draws); the rounding units left over go to the segments with the largest
    fractional remainders, ties to the earlier series.
    """
    scale = 10**fmt.magnitude
    decimals = _decimals(
        [*(v / scale for v in values if v is not None), total / scale], fmt.decimals
    )
    unit = 10**decimals
    floors = _floors(
        [None if v is None else v / scale * unit for v in values], round(total / scale * unit)
    )
    return tuple(
        None if i not in floors else format_value(floors[i] / unit * scale, fmt)
        for i in range(len(values))
    )


def consistent_shares(
    values: Sequence[float | None], total: float, fmt: Format
) -> tuple[str | None, ...]:
    """The percentage labels of one column or pie: rounded so they add up to exactly 100 %.

    Like :func:`consistent`, but for shares: every positive value becomes its percentage of
    ``total`` (negative and empty ones keep their place without a label, the rule of
    ``percent.share``), rounded at the share precision (``fmt.decimals``, else one decimal).
    """
    decimals = 1 if fmt.decimals is None else fmt.decimals
    unit = 10**decimals
    shares = [share(v, total) for v in values]
    floors = _floors([None if p is None else p * unit for p in shares], round(100 * unit))
    return tuple(
        None if i not in floors else format_share(floors[i] / unit, fmt) for i in range(len(values))
    )


def _floors(scaled: Sequence[float | None], target: int) -> dict[int, int]:
    """The floor of every scaled value, raised so that the floors sum to ``target``.

    ``target`` is the rounded sum the floors have to reach; the units left over go to the
    largest remainders, ties to the earlier index. The leftover count cannot exceed the number
    of values, so every remainder is used at most once.
    """
    floors: dict[int, int] = {}
    remainders: list[tuple[float, int]] = []
    used = 0
    for i, value in enumerate(scaled):
        if value is None:
            continue
        floor = math.floor(value)
        floors[i] = floor
        remainders.append((value - floor, i))
        used += floor
    remainders.sort(key=lambda r: (-r[0], r[1]))
    for _, i in remainders[: max(target - used, 0)]:
        floors[i] += 1
    return floors


def _decimals(values: Sequence[float], decimals: int | None) -> int:
    """The precision the labels are rounded at: the format's, or the automatic rule."""
    if decimals is not None:
        return decimals
    return 0 if all(v == round(v) for v in values) else 2
