"""Table layout: the chart data sheet drawn as a styled grid (M25)."""

from __future__ import annotations

from librecharts.core import elements
from librecharts.core.layout.common import format_value
from librecharts.core.model import Format
from librecharts.core.primitives import (
    BACKGROUND,
    SHADE,
    Line,
    Polygon,
    Polyline,
    Primitive,
    Rect,
    Text,
)
from librecharts.core.table import Cell, TableData, column_widths, heatmap_range


def layout_table(
    data: TableData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Cell rectangles, borders, text and typed markers in a grid."""
    fmt = fmt or Format()
    if not data.cells or not data.cells[0]:
        return ()
    rows, columns = len(data.cells), max(len(row) for row in data.cells)
    widths = column_widths(data.spec, columns)
    row_height = data.spec.row_height or height / rows
    lefts = [0.0]
    for share in widths:
        lefts.append(lefts[-1] + share * width)
    low, high = heatmap_range(data)
    out: list[Primitive] = []
    for row_index, row in enumerate(data.cells):
        top = row_index * row_height
        for column in range(columns):
            cell = row[column] if column < len(row) else Cell("empty")
            x = lefts[column]
            cell_width = lefts[column + 1] - x
            header = data.spec.header and row_index == 0
            zebra = data.spec.zebra and row_index % 2 == 1 and not header
            series = SHADE if header or zebra else BACKGROUND
            if (
                data.spec.heatmap
                and cell.kind == "number"
                and cell.number is not None
                and high > low
            ):
                series = round((cell.number - low) / (high - low) * 5)
            out.append(Rect(x, top, cell_width, row_height, series, category=column))
            if data.spec.borders:
                out.append(Line(x, top, x + cell_width, top, "grid"))
                out.append(Line(x, top, x, top + row_height, "grid"))
            out.extend(_content(cell, x, top, cell_width, row_height, fmt))
    if data.spec.borders:
        out.append(Line(lefts[-1], 0, lefts[-1], rows * row_height, "grid"))
        out.append(Line(0, rows * row_height, lefts[-1], rows * row_height, "grid"))
    return tuple(out)


def _content(
    cell: Cell, x: float, top: float, width: float, height: float, fmt: Format
) -> list[Primitive]:
    if cell.kind == "harvey":
        return _shifted(
            elements.layout_element(elements.Element.harvey(int(cell.number or 0)), width, height),
            x,
            top,
        )
    if cell.kind == "check":
        return _shifted(
            elements.layout_element(elements.Element.check(cell.check), width, height), x, top
        )
    if cell.kind == "spark" and cell.spark:
        points = list(cell.spark)
        low, high = min(points), max(points)
        span = high - low or 1.0
        step = width / max(len(points) - 1, 1)
        return [
            Polyline(
                tuple(
                    (x + index * step, top + height - (value - low) / span * height)
                    for index, value in enumerate(points)
                ),
                0,
            )
        ]
    if cell.kind == "number":
        return [
            Text(
                x,
                top,
                width - 100,
                height,
                format_value(cell.number or 0.0, fmt),
                "right",
                "value",
            )
        ]
    if cell.kind == "text":
        return [Text(x + 100, top, width - 200, height, cell.text, "left", "value")]
    return []


def _shifted(primitives: tuple[Primitive, ...], dx: float, dy: float) -> list[Primitive]:
    from dataclasses import replace

    out: list[Primitive] = []
    for primitive in primitives:
        if isinstance(primitive, (Rect, Text)):
            out.append(replace(primitive, x=primitive.x + dx, y=primitive.y + dy))
        elif isinstance(primitive, Line):
            out.append(
                replace(
                    primitive,
                    x1=primitive.x1 + dx,
                    y1=primitive.y1 + dy,
                    x2=primitive.x2 + dx,
                    y2=primitive.y2 + dy,
                )
            )
        elif isinstance(primitive, (Polyline, Polygon)):
            out.append(
                replace(
                    primitive,
                    points=tuple((px + dx, py + dy) for px, py in primitive.points),
                )
            )
        else:
            out.append(primitive)
    return out
