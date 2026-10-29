"""Label placement: value labels and totals the user moved by hand (M13, ADR 0023).

The layout puts every value label and total where it belongs and gives it a :class:`LabelKey`. A
chart remembers a moved label as a :class:`LabelOffset` from that place, so the label follows its
segment through data edits, sorting and resizing. :func:`place` applies the offsets to laid-out
primitives; :func:`moved` is the reverse step for the adapter, which reads where the user dragged
a label. Offsets never add, remove or reorder primitives: the structure stays independent of the
size and of the offsets (ADR 0007).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from librecharts.core.layout.common import LABEL_HEIGHT
from librecharts.core.model import ChartState, LabelOffset
from librecharts.core.primitives import Polygon, Primitive, Rect, Text, bounds

SNAP = 100.0  # 1/100 mm: a label dragged back to within 1 mm of its place snaps there
TOLERANCE = 2.0  # 1/100 mm: LibreOffice rounds geometry, so equal boxes differ by a little

Box = tuple[float, float, float, float]  # x, y, width, height


def movable(state: ChartState) -> bool:
    """Whether the chart has labels the user can move (every kind but Gantt)."""
    return state.kind != "gantt"


def keyed(
    primitives: tuple[Primitive, ...], order: tuple[int, ...] | None
) -> tuple[Primitive, ...]:
    """``primitives`` with the categories of their label keys moved from display to data indices.

    ``order`` is the sort permutation (display position -> data sheet index), ``None`` for none.
    """
    if order is None or order == tuple(range(len(order))):
        return primitives
    return tuple(
        replace(p, key=replace(p.key, category=order[p.key.category]))
        if isinstance(p, Text) and p.key is not None and p.key.category < len(order)
        else p
        for p in primitives
    )


def place(
    primitives: tuple[Primitive, ...], offsets: tuple[LabelOffset, ...]
) -> tuple[Primitive, ...]:
    """Move every keyed label by its offset, reveal it and recolour it for its new background.

    The label's box is at least ``LABEL_HEIGHT`` high around its new centre. Its ``fill`` becomes
    the data shape under that centre (its own segment, another one, or none), so a label moved out
    of a dark segment does not keep white text. Offsets whose label does not exist are ignored.
    """
    if not offsets:
        return primitives
    by_key = {offset.key: offset for offset in offsets}
    out: list[Primitive] = []
    for p in primitives:
        offset = by_key.get(p.key) if isinstance(p, Text) and p.key is not None else None
        if not isinstance(p, Text) or offset is None:
            out.append(p)
            continue
        centre_x = p.x + p.width / 2 + offset.dx
        centre_y = p.y + p.height / 2 + offset.dy
        height = max(p.height, LABEL_HEIGHT)
        out.append(
            replace(
                p,
                x=centre_x - p.width / 2,
                y=centre_y - height / 2,
                height=height,
                fill=_fill_under(primitives, centre_x, centre_y),
                hidden=False,
            )
        )
    return tuple(out)


def moved(
    laid_out: tuple[Primitive, ...], current: Sequence[Box], offsets: tuple[LabelOffset, ...]
) -> tuple[LabelOffset, ...] | None:
    """The offsets after the user dragged labels: ``laid_out`` is what the chart's state draws,
    ``current`` the box of every child shape (frame excluded) in chart coordinates.

    Returns ``None`` if anything but keyed labels differs (a resize, a redraw in progress, a bar
    moved by hand): that is not a label move. An offset below 1 mm on both axes is dropped, so a
    label dragged back onto its place snaps there. The result equals ``offsets`` if nothing moved.
    """
    if len(current) != len(laid_out):
        return None
    known = {offset.key: offset for offset in offsets}
    result = dict(known)
    for p, box in zip(laid_out, current, strict=True):
        x, y, width, height = bounds(p)
        if isinstance(p, Text) and p.key is not None:
            dx = box[0] + box[2] / 2 - (x + width / 2)
            dy = box[1] + box[3] / 2 - (y + height / 2)
            if abs(dx) <= TOLERANCE and abs(dy) <= TOLERANCE:
                continue
            before = known.get(p.key)
            result[p.key] = LabelOffset(
                p.key,
                (before.dx if before else 0.0) + dx,
                (before.dy if before else 0.0) + dy,
            )
        elif any(abs(a - b) > TOLERANCE for a, b in zip(box, (x, y, width, height), strict=True)):
            return None
    return tuple(o for o in result.values() if max(abs(o.dx), abs(o.dy)) >= SNAP)


def _fill_under(primitives: tuple[Primitive, ...], x: float, y: float) -> int | None:
    """The series of the topmost data shape that covers (``x``, ``y``), if any."""
    for p in reversed(primitives):
        if isinstance(p, Rect) and p.series >= 0:
            if p.x <= x <= p.x + p.width and p.y <= y <= p.y + p.height:
                return p.series
        elif isinstance(p, Polygon) and not p.outline and p.series >= 0 and _inside(p.points, x, y):
            return p.series
    return None


def _inside(points: tuple[tuple[float, float], ...], x: float, y: float) -> bool:
    """Whether (``x``, ``y``) is inside the polygon (ray casting)."""
    inside = False
    for (x1, y1), (x2, y2) in zip(points, (*points[1:], points[0]), strict=True):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
            inside = not inside
    return inside
