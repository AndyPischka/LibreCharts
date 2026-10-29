"""Slide elements: Harvey balls and check marks (ADR 0021).

An element is a group of native shapes like a chart, but its whole state is the group name, so
copies and pasting into other presentations need no stored state. Names end in a letter, because
LibreOffice cuts trailing digits off the name of a copy (see ``lo/store.py``) and appends `` 1``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from librecharts.core.geometry import polar, sector
from librecharts.core.primitives import NEGATIVE, POSITIVE, Polygon, Polyline, Primitive

ElementKind = Literal["harvey", "check"]

PREFIX = "librecharts-element:"
HARVEY_LEVELS = (0, 25, 50, 75, 100)
CHECK_SYMBOLS = ("tick", "cross", "empty")
DEFAULT_SIZE = 600  # 1/100 mm; a new element is 0.6 cm square

_NAME = re.compile(
    re.escape(PREFIX)
    + r"(?:harvey:(?P<level>0|25|50|75|100)%|check:(?P<symbol>tick|cross|empty))"
    + r"(?: \d+)?"  # the suffix LibreOffice adds to a copy
)


@dataclass(frozen=True, slots=True)
class Element:
    """``value`` is the fill level in percent (Harvey ball) or the symbol name (check mark)."""

    kind: ElementKind
    value: str

    @staticmethod
    def harvey(level: int) -> Element:
        if level not in HARVEY_LEVELS:
            raise ValueError(f"a Harvey ball is filled to one of {HARVEY_LEVELS} percent")
        return Element("harvey", str(level))

    @staticmethod
    def check(symbol: str) -> Element:
        if symbol not in CHECK_SYMBOLS:
            raise ValueError(f"a check mark is one of {CHECK_SYMBOLS}")
        return Element("check", symbol)


def name(element: Element) -> str:
    """The group name that stores ``element``."""
    if element.kind == "harvey":
        return f"{PREFIX}harvey:{element.value}%"
    return f"{PREFIX}check:{element.value}"


def parse(group_name: str) -> Element | None:
    """The element a group name stands for, or ``None`` if it is not an element's name."""
    match = _NAME.fullmatch(group_name)
    if match is None:
        return None
    if match["level"] is not None:
        return Element("harvey", match["level"])
    return Element("check", match["symbol"])


def following(element: Element) -> Element:
    """The next state in the cycle (0, 25, ... 100 %, then 0 again; tick, cross, empty)."""
    states = [str(level) for level in HARVEY_LEVELS] if element.kind == "harvey" else CHECK_SYMBOLS
    return Element(element.kind, states[(list(states).index(element.value) + 1) % len(states)])


def parse_query(query: str) -> Element:
    """``harvey=50`` or ``check=cross`` (the argument of ``SetElement``); ``ValueError`` if bad."""
    key, _, value = query.partition("=")
    if key == "harvey" and value.isdigit():
        return Element.harvey(int(value))
    if key == "check":
        return Element.check(value)
    raise ValueError(f"unknown element {query!r}")


def _circle(cx: float, cy: float, radius: float) -> Polygon:
    return Polygon(tuple(polar(cx, cy, radius, angle) for angle in range(360)), 0, True)


def layout_element(element: Element, width: float, height: float) -> tuple[Primitive, ...]:
    """The primitives of ``element``: a square as large as fits, centred in the box.

    The structure depends on the element's state only, never on the size (ADR 0007).
    """
    side = min(width, height)
    left, top = (width - side) / 2, (height - side) / 2
    radius = side / 2
    cx, cy = left + radius, top + radius

    def at(fx: float, fy: float) -> tuple[float, float]:
        return left + fx * side, top + fy * side

    if element.kind == "harvey":
        level = int(element.value)
        if level == 0:
            return (_circle(cx, cy, radius),)
        return (
            _circle(cx, cy, radius),
            Polygon(sector(cx, cy, radius, 0, 0, level * 3.6), 0),
        )
    if element.value == "tick":
        return (Polyline((at(0.18, 0.55), at(0.40, 0.80), at(0.84, 0.22)), POSITIVE),)
    if element.value == "cross":
        return (
            Polyline((at(0.20, 0.20), at(0.80, 0.80)), NEGATIVE),
            Polyline((at(0.80, 0.20), at(0.20, 0.80)), NEGATIVE),
        )
    return (_circle(cx, cy, radius),)
