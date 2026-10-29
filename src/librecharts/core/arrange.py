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


def swap(first: Rect, second: Rect) -> tuple[Rect, Rect]:
    """The two rectangles with their centres exchanged; sizes stay."""
    (x1, y1, w1, h1), (x2, y2, w2, h2) = first, second
    cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2
    cx2, cy2 = x2 + w2 / 2, y2 + h2 / 2
    return (
        (round(cx2 - w1 / 2), round(cy2 - h1 / 2), w1, h1),
        (round(cx1 - w2 / 2), round(cy1 - h2 / 2), w2, h2),
    )
