"""Process, chevron and pyramid graphics and icons (M26).

The graphic's state lives in its group name (``librecharts-graphic:process:4:horizontal``); the
step texts are child shapes, so no document property is needed. :func:`layout` returns the
primitives for a box; the labels are the text primitives in reading order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from librecharts.core import icons
from librecharts.core.primitives import Polygon, Primitive, Rect, Text

GraphicKind = Literal["process", "chevron", "pyramid", "icon"]
PREFIX = "librecharts-graphic:"
MAX_STEPS = 8


@dataclass(frozen=True, slots=True)
class Graphic:
    kind: GraphicKind
    steps: int = 4
    horizontal: bool = True
    icon: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("process", "chevron", "pyramid", "icon"):
            raise ValueError(f"unknown graphic kind: {self.kind!r}")
        if self.kind == "icon":
            if self.icon not in icons.ICONS:
                raise ValueError(f"unknown icon: {self.icon!r}")
            return
        if not 1 <= self.steps <= MAX_STEPS:
            raise ValueError(f"a graphic has 1 to {MAX_STEPS} steps")
        if self.kind == "pyramid" and self.horizontal:
            raise ValueError("a pyramid is vertical")


def name(graphic: Graphic) -> str:
    if graphic.kind == "icon":
        return f"{PREFIX}icon:{graphic.icon}"
    orientation = "horizontal" if graphic.horizontal else "vertical"
    return f"{PREFIX}{graphic.kind}:{graphic.steps}:{orientation}"


def parse(group_name: str) -> Graphic | None:
    """The graphic a group name describes, or ``None`` for any other name."""
    if not group_name.startswith(PREFIX):
        return None
    parts = group_name[len(PREFIX) :].split(":")
    try:
        if parts[0] == "icon" and len(parts) >= 2:
            return Graphic("icon", icon=parts[1])
        if parts[0] in ("process", "chevron", "pyramid") and len(parts) >= 3:
            return Graphic(
                parts[0],  # pyright: ignore[reportArgumentType]
                int(parts[1]),
                parts[2] == "horizontal",
            )
    except ValueError:
        return None
    return None


def layout(
    graphic: Graphic, width: float, height: float, labels: tuple[str, ...] = ()
) -> tuple[Primitive, ...]:
    """Primitives for ``graphic`` in a box; text primitives in reading order."""
    if graphic.kind == "icon":
        return icons.primitives(graphic.icon, width, height)
    labels = labels or tuple(f"Step {index + 1}" for index in range(graphic.steps))
    if graphic.kind == "process":
        return _process(graphic.steps, width, height, labels, graphic.horizontal)
    if graphic.kind == "chevron":
        return _chevron(graphic.steps, width, height, labels, graphic.horizontal)
    return _pyramid(graphic.steps, width, height, labels)


def _process(
    steps: int, width: float, height: float, labels: tuple[str, ...], horizontal: bool
) -> tuple[Primitive, ...]:
    out: list[Primitive] = []
    gap = min(width, height) * 0.04
    if horizontal:
        cell = (width - gap * (steps - 1)) / steps
        for index in range(steps):
            x = index * (cell + gap)
            out.append(Rect(x, 0, cell, height, index % 6))
            out.append(Text(x, 0, cell, height, labels[index], "center", "value"))
    else:
        cell = (height - gap * (steps - 1)) / steps
        for index in range(steps):
            y = index * (cell + gap)
            out.append(Rect(0, y, width, cell, index % 6))
            out.append(Text(0, y, width, cell, labels[index], "center", "value"))
    return tuple(out)


def _chevron(
    steps: int, width: float, height: float, labels: tuple[str, ...], horizontal: bool
) -> tuple[Primitive, ...]:
    out: list[Primitive] = []
    if horizontal:
        notch = height * 0.25
        cell = width / steps
        for index in range(steps):
            left, right = index * cell, (index + 1) * cell
            points = (
                (left, 0),
                (right - notch, 0),
                (right, height / 2),
                (right - notch, height),
                (left, height),
                (left + (notch if index else 0), height / 2),
            )
            out.append(Polygon(tuple(points), index % 6))
            out.append(
                Text(left + notch, 0, cell - 2 * notch, height, labels[index], "center", "value")
            )
    else:
        notch = width * 0.2
        cell = height / steps
        for index in range(steps):
            top, bottom = index * cell, (index + 1) * cell
            points = (
                (0, top),
                (width, top),
                (width, bottom),
                (0, bottom),
                (width / 2, bottom - (notch if index else 0)),
            )
            out.append(Polygon(tuple(points), index % 6))
            out.append(Text(0, top, width, cell - notch, labels[index], "center", "value"))
    return tuple(out)


def _pyramid(
    steps: int, width: float, height: float, labels: tuple[str, ...]
) -> tuple[Primitive, ...]:
    out: list[Primitive] = []
    cell = height / steps
    for index in range(steps):
        top, bottom = index * cell, (index + 1) * cell
        narrow = width * index / (steps * 2)
        wide = width * (index + 1) / (steps * 2)
        points = (
            (narrow, top),
            (width - narrow, top),
            (width - wide, bottom),
            (wide, bottom),
        )
        out.append(Polygon(tuple(points), index % 6))
        out.append(Text(width * 0.2, top, width * 0.6, cell, labels[index], "center", "value"))
    return tuple(out)
