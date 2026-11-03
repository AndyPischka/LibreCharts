"""Category order of a column or bar chart (M5, "sort by value").

Sorting is a display option: the data sheet and the stored annotations keep their indices. The
layout applies the permutation returned here, and picking maps a clicked display position back.
"""

from __future__ import annotations

from dataclasses import replace

from librecharts.core.datasheet import ChartData
from librecharts.core.model import (
    AXIS_ANNOTATIONS,
    Annotation,
    Grouping,
    SortOrder,
)


def order(data: ChartData, grouping: Grouping, sort: SortOrder) -> tuple[int, ...]:
    """A permutation of the category indices: display position -> data sheet index.

    Stacked charts sort by the column sum, clustered ones by the first series (the one that
    keeps the categories apart). Empty categories go last, independently of the direction; ties
    keep their data sheet order.
    """
    count = len(data.categories)
    if sort == "none" or count < 2:
        return tuple(range(count))
    sign = -1 if sort == "descending" else 1

    def key(category: int) -> tuple[int, float]:
        value = _key(data, grouping, category)
        return (1, 0.0) if value is None else (0, sign * value)

    return tuple(sorted(range(count), key=key))


def sorted_data(data: ChartData, order: tuple[int, ...]) -> ChartData:
    """``data`` with categories (and every series' values) in display order."""
    return ChartData(
        tuple(data.categories[i] for i in order),
        tuple(replace(s, values=tuple(s.values[i] for i in order)) for s in data.series),
    )


def display_index(order: tuple[int, ...]) -> dict[int, int]:
    """Data sheet index -> display position."""
    return {category: display for display, category in enumerate(order)}


def remap(annotations: tuple[Annotation, ...], order: tuple[int, ...]) -> tuple[Annotation, ...]:
    """``annotations`` with category indices moved to where sorting draws them.

    Axis annotations (axis breaks, value lines) belong to the whole axis. A category gap follows
    its two categories and is not drawn when sorting separates them; a group bracket connects its
    two end categories, so it spans whatever lies between them in display order. Annotations
    pointing past the data keep their index and stay undrawn; undoing a data edit or the sort
    brings them back.
    """
    if order == tuple(range(len(order))):
        return annotations
    positions = display_index(order)
    out: list[Annotation] = []
    for annotation in annotations:
        if annotation.kind in AXIS_ANNOTATIONS:
            out.append(annotation)
            continue
        if annotation.kind == "category_gap":
            first = positions.get(annotation.start)
            last = positions.get(annotation.end)
            if first is not None and last == first + 1:
                out.append(replace(annotation, start=first, end=last))
            continue
        if annotation.kind == "group_bracket":
            first, last = sorted(
                (
                    positions.get(annotation.start, annotation.start),
                    positions.get(annotation.end, annotation.end),
                )
            )
            out.append(replace(annotation, start=first, end=last))
            continue
        out.append(
            replace(
                annotation,
                start=positions.get(annotation.start, annotation.start),
                end=positions.get(annotation.end, annotation.end),
            )
        )
    return tuple(out)


def _key(data: ChartData, grouping: Grouping, category: int) -> float | None:
    if grouping == "clustered":
        if not data.series:
            return None
        return data.series[0].values[category]
    values = [v for s in data.series if (v := s.values[category]) is not None]
    return sum(values) if values else None
