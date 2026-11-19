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
from urllib.parse import parse_qs

from librecharts.core.layout.common import LABEL_HEIGHT
from librecharts.core.model import ChartState, LabelKey, LabelOffset
from librecharts.core.primitives import Polygon, Primitive, Rect, Text, bounds

SNAP = 100.0  # 1/100 mm: a label dragged back to within 1 mm of its place snaps there
TOLERANCE = 2.0  # 1/100 mm: LibreOffice rounds geometry, so equal boxes differ by a little
PREFIX = "librecharts-label:"

Box = tuple[float, float, float, float]  # x, y, width, height


def key_from_name(name: str) -> LabelKey | None:
    """The label key written into a shape name, or ``None`` for any other shape (M22)."""
    if not name.startswith(PREFIX):
        return None
    parts = name[len(PREFIX) :].split(":")
    if len(parts) != 3:
        return None
    role, category, series = parts
    try:
        return LabelKey(
            role,  # pyright: ignore[reportArgumentType]
            int(category),
            None if not series else int(series),
        )
    except ValueError:
        return None


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
    """Apply label overrides and offsets: move, hide, retitle and recolour keyed labels.

    A moved label's box is at least ``LABEL_HEIGHT`` high around its new centre. Its ``fill``
    becomes the data shape under that centre (its own segment, another one, or none), so a label
    moved out of a dark segment does not keep white text. An offset of zero only changes the text
    or visibility, never the box. Overrides whose label does not exist are ignored.
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
        if offset.dx or offset.dy:
            centre_x = p.x + p.width / 2 + offset.dx
            centre_y = p.y + p.height / 2 + offset.dy
            height = max(p.height, LABEL_HEIGHT)
            p = replace(
                p,
                x=centre_x - p.width / 2,
                y=centre_y - height / 2,
                height=height,
                fill=_fill_under(primitives, centre_x, centre_y),
                hidden=False,
            )
        if offset.hidden:
            p = replace(p, hidden=True)
        elif offset.text:
            p = replace(p, text=offset.text, hidden=False)
        out.append(p)
    return tuple(out)


def override(state: ChartState, query: str, *, command: str = "SetLabel") -> ChartState:
    """``state`` with the label override in ``query`` applied; one undo step.

    ``role``, ``category`` and optionally ``series`` name the label (``LabelKey``).
    ``SetLabel`` takes ``hidden=true|false``; ``SetLabelText`` takes ``text=...`` (empty clears
    the custom text); ``ResetLabel`` removes the whole override. Invalid arguments raise
    ``ValueError``.
    """
    args = {
        key: values[-1]
        for key, values in parse_qs(query, strict_parsing=True, keep_blank_values=True).items()
    }
    try:
        key = LabelKey(
            args.get("role", "value"),  # pyright: ignore[reportArgumentType]
            int(args["category"]),
            None if "series" not in args else int(args["series"]),
        )
    except (KeyError, ValueError) as exc:
        raise ValueError("a label override needs role, category and optional series") from exc
    existing = next((offset for offset in state.labels if offset.key == key), None)
    if command == "ResetLabel":
        wanted = None
    else:
        dx = existing.dx if existing else 0.0
        dy = existing.dy if existing else 0.0
        hidden = existing.hidden if existing else False
        text = existing.text if existing else ""
        if "hidden" in args:
            flag = {"true": True, "false": False}.get(args["hidden"])
            if flag is None:
                raise ValueError("hidden must be true or false")
            hidden = flag
        if "text" in args:
            text = args["text"]
            if len(text) > 80:
                raise ValueError("a label text must be at most 80 characters")
            if text:
                hidden = False
        if not dx and not dy and not hidden and not text:
            wanted = None
        else:
            wanted = LabelOffset(key, dx, dy, hidden, text)
    labels = [offset for offset in state.labels if offset.key != key]
    if wanted is not None:
        labels.append(wanted)
    if labels == list(state.labels):
        return state
    return replace(state, labels=tuple(labels))


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
                before.hidden if before else False,
                before.text if before else "",
            )
        elif any(abs(a - b) > TOLERANCE for a, b in zip(box, (x, y, width, height), strict=True)):
            return None
    return tuple(
        o for o in result.values() if max(abs(o.dx), abs(o.dy)) >= SNAP or o.hidden or o.text
    )


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
