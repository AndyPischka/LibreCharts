"""Arranging shapes: same size, grid, swap (M12). Pure geometry on rectangles.

A rectangle is ``(x, y, width, height)`` in 1/100 mm. Every function returns new rectangles in the
order of its input.
"""

from __future__ import annotations

Rect = tuple[int, int, int, int]


def same_width(rects: list[Rect]) -> list[Rect]:
    """All as wide as the widest; left edges stay."""
    widest = max((w for _, _, w, _ in rects), default=0)
    return [(x, y, widest, h) for x, y, _, h in rects]


def same_height(rects: list[Rect]) -> list[Rect]:
    """All as high as the highest; top edges stay."""
    highest = max((h for _, _, _, h in rects), default=0)
    return [(x, y, w, highest) for x, y, w, _ in rects]


def same_size(rects: list[Rect]) -> list[Rect]:
    """All as wide as the widest and as high as the highest; top-left corners stay."""
    return same_height(same_width(rects))


def grid(rects: list[Rect], columns: int, gap: int) -> list[Rect]:
    """Arrange in rows of ``columns`` with ``gap`` between columns and rows.

    The shapes keep their reading order (top to bottom, then left to right), the top-left corner
    of the selection stays, a column is as wide as its widest shape and a row as high as its
    highest. Shapes sit at the top-left of their cell.
    """
    if columns < 1 or gap < 0:
        raise ValueError("a grid needs at least one column and a gap of zero or more")
    if not rects:
        return []
    order = sorted(range(len(rects)), key=lambda i: (rects[i][1], rects[i][0], i))
    rows = [order[start : start + columns] for start in range(0, len(order), columns)]
    widths = [
        max((rects[row[c]][2] for row in rows if c < len(row)), default=0) for c in range(columns)
    ]
    heights = [max(rects[i][3] for i in row) for row in rows]
    left = min(x for x, _, _, _ in rects)
    top = min(y for _, y, _, _ in rects)
    placed = list(rects)
    y = top
    for row, height in zip(rows, heights, strict=True):
        x = left
        for column, i in enumerate(row):
            placed[i] = (x, y, rects[i][2], rects[i][3])
            x += widths[column] + gap
        y += height + gap
    return placed


def distribute(rects: list[Rect], axis: str = "h", mode: str = "gaps") -> list[Rect]:
    """Equal gaps or equal centres along ``axis``; the outermost shapes stay.

    Shapes are ordered by their position, not by selection order. Fewer than three shapes (or two
    for equal centres) are returned unchanged.
    """
    if axis not in ("h", "v") or mode not in ("gaps", "centres"):
        raise ValueError("distribute needs axis h/v and mode gaps/centres")
    if len(rects) < 3:
        return list(rects)
    start, size = (0, 2) if axis == "h" else (1, 3)
    order = sorted(range(len(rects)), key=lambda i: (rects[i][start], i))
    first, last = rects[order[0]], rects[order[-1]]
    span = (last[start] + last[size]) - first[start]
    sizes = sum(rects[i][size] for i in order)
    placed = list(rects)
    if mode == "gaps":
        gap = (span - sizes) / (len(order) - 1)
        position = first[start] + first[size] + gap
        for index in order[1:-1]:
            coordinates = list(rects[index])
            coordinates[start] = round(position)
            placed[index] = tuple(coordinates)  # type: ignore[assignment]
            position += rects[index][size] + gap
    else:
        first_centre = first[start] + first[size] / 2
        last_centre = last[start] + last[size] / 2
        step = (last_centre - first_centre) / (len(order) - 1)
        for rank, index in enumerate(order[1:-1], start=1):
            coordinates = list(rects[index])
            coordinates[start] = round(first_centre + rank * step - rects[index][size] / 2)
            placed[index] = tuple(coordinates)  # type: ignore[assignment]
    return placed


def align(rects: list[Rect], edge: str) -> list[Rect]:
    """Align every shape's ``left``, ``right``, ``top``, ``bottom``, ``hcenter`` or ``vcenter``.

    The anchor is the selection's bounding box.
    """
    if not rects:
        return []
    if edge not in ("left", "right", "top", "bottom", "hcenter", "vcenter"):
        raise ValueError(f"unknown align edge: {edge!r}")
    left = min(x for x, _, _, _ in rects)
    right = max(x + w for x, _, w, _ in rects)
    top = min(y for _, y, _, _ in rects)
    bottom = max(y + h for _, y, _, h in rects)
    out: list[Rect] = []
    for x, y, width, height in rects:
        if edge == "left":
            x = left
        elif edge == "right":
            x = right - width
        elif edge == "hcenter":
            x = round((left + right - width) / 2)
        elif edge == "top":
            y = top
        elif edge == "bottom":
            y = bottom - height
        else:
            y = round((top + bottom - height) / 2)
        out.append((x, y, width, height))
    return out


def align_slide(
    rects: list[Rect], edge: str, width: int, height: int, margin: int = 0
) -> list[Rect]:
    """Align shapes against the slide edges with an optional margin."""
    if edge not in ("left", "right", "top", "bottom", "hcenter", "vcenter"):
        raise ValueError(f"unknown align edge: {edge!r}")
    out: list[Rect] = []
    for x, y, w, h in rects:
        if edge == "left":
            x = margin
        elif edge == "right":
            x = width - w - margin
        elif edge == "hcenter":
            x = round((width - w) / 2)
        elif edge == "top":
            y = margin
        elif edge == "bottom":
            y = height - h - margin
        else:
            y = round((height - h) / 2)
        out.append((x, y, w, h))
    return out


def swap(first: Rect, second: Rect) -> tuple[Rect, Rect]:
    """The two rectangles with their centres exchanged; sizes stay."""
    (x1, y1, w1, h1), (x2, y2, w2, h2) = first, second
    cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2
    cx2, cy2 = x2 + w2 / 2, y2 + h2 / 2
    return (
        (round(cx2 - w1 / 2), round(cy2 - h1 / 2), w1, h1),
        (round(cx1 - w2 / 2), round(cy1 - h2 / 2), w2, h2),
    )
