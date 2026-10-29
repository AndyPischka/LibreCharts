"""Layout of Gantt charts: a label column, a two-level date header and one band per row (M10).

Bars run from the start of their first day to the end of their last day; milestones are diamonds of
fixed size in the middle of their day, labelled with their date; a phase is a thin bar in its colour
with ticks down at both ends, its label bold like a heading's. A remark goes right of the row's
mark, left of it when the mark ends in the last quarter of the scale, or inside a bar that spans
nearly the whole scale; the choice follows the dates, not the size. Every other unit of the upper
level is shaded; gridlines (optional) mark the lower level. Date lines (value lines whose value is a
serial number) are dashed vertical lines with their date below the rows.

The kinds and order of the primitives depend on the data only, never on the size (ADR 0007).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.datasheet import ChartData
from librecharts.core.gantt import GanttData, Row, starts, to_date
from librecharts.core.layout.common import LABEL_HEIGHT, TICK_GAP
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import SHADE, Line, Polygon, Primitive, Rect, Text, TextRole
from librecharts.core.timescale import TimeScale, format_date, label, time_scale

HEADER_ROW = 500.0  # height of each of the two header levels
HEADER_GAP = 100.0  # between the header and the first row
CHAR_WIDTH = 190.0  # estimated width of one label character, for the label column
MIN_LABEL_WIDTH = 1500.0
MAX_LABEL_SHARE = 0.35  # the label column takes at most this share of the chart width
LABEL_PADDING = 200.0  # between the label column and the time area
RIGHT_PADDING = 300.0  # right of the time area
BAR_RATIO = 0.6  # bar thickness as a share of the row height
PHASE_RATIO = 0.2  # thickness of a phase bar as a share of the row height
DIAMOND = 400.0  # milestone diamond, 1/100 mm; shrinks only to fit low rows
SIDE_GAP = 120.0  # between a mark and its remark
SIDE_WIDTH = 3000.0  # width of a remark box
RIGHT_LIMIT = 0.75  # a remark goes right of a mark that ends up to here (share of the scale)
LEFT_LIMIT = 0.25  # else left of a mark that starts from here, else inside the bar
DATE_BAND = 700.0  # below the rows, for the labels of date lines
DATE_LABEL_WIDTH = 2400.0

_X = Callable[[date], float]


def layout_gantt(
    data: GanttData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the rows.
    """
    fmt = fmt or Format()
    measured = starts(data)
    lines = notes.value_lines(annotations, measured, "gantt")
    longest = max((len(row.label) for row in data.rows), default=0)
    label_width = min(
        max(MIN_LABEL_WIDTH, longest * CHAR_WIDTH + LABEL_PADDING), width * MAX_LABEL_SHARE
    )
    time_left = label_width
    time_width = width - time_left - RIGHT_PADDING
    header_bottom = 2 * HEADER_ROW
    rows_top = header_bottom + HEADER_GAP
    rows_bottom = height - (DATE_BAND if lines else 0.0)
    if time_width <= 0 or rows_bottom <= rows_top:
        raise ValueError("chart area too small")

    marked = [_line_day(annotation, measured) for annotation in lines]
    days = [day for row in data.dated for day in (row.start, row.end) if day is not None]
    days += [day for day in marked if day is not None]
    if not days:
        return ()
    scale = time_scale(min(days), max(days))
    day_width = time_width / scale.days
    with_year = scale.years > 1

    def x(day: date) -> float:
        return time_left + scale.fraction(day) * time_width

    out: list[Primitive] = []
    for index, period in enumerate(scale.periods(scale.upper)):
        if index % 2:
            out.append(
                Rect(
                    x(period.start),
                    rows_top,
                    x(period.end) - x(period.start),
                    rows_bottom - rows_top,
                    SHADE,
                )
            )
    if fmt.gridlines:
        out.extend(
            Line(x(period.start), HEADER_ROW, x(period.start), rows_bottom, "grid")
            for period in scale.periods(scale.lower)[1:]
        )
    out.extend(_header(scale, x, fmt.language))

    slot = (rows_bottom - rows_top) / len(data.rows)
    for index, row in enumerate(data.rows):
        top = rows_top + index * slot
        if row.label:
            role: TextRole = "heading" if row.kind in ("phase", "heading") else "category"
            out.append(Text(0, top, label_width - LABEL_PADDING, slot, row.label, "left", role))
        if row.start is None or row.end is None:
            continue
        out.extend(_row(row, row.start, row.end, scale, x, day_width, top, slot, fmt, with_year))

    for day in marked:
        if day is None:
            continue
        centre = x(day) + day_width / 2
        out.append(Line(centre, rows_top, centre, rows_bottom, "helper"))
        out.append(
            Text(
                centre - DATE_LABEL_WIDTH / 2,
                rows_bottom + TICK_GAP,
                DATE_LABEL_WIDTH,
                LABEL_HEIGHT,
                format_date(day, fmt.language, with_year=with_year),
                "center",
                "annotation",
            )
        )
    return tuple(out)


def _line_day(annotation: Annotation, measured: ChartData) -> date | None:
    level = value_line.resolved(annotation, measured)
    return None if level is None else to_date(level)


def _row(
    row: Row,
    start: date,
    end: date,
    scale: TimeScale,
    x: _X,
    day_width: float,
    top: float,
    slot: float,
    fmt: Format,
    with_year: bool,
) -> list[Primitive]:
    """The mark of one dated row and its side text (remark, a milestone's date)."""
    centre_y = top + slot / 2
    out: list[Primitive] = []
    side = row.remark
    if row.kind == "milestone":
        half = min(DIAMOND, slot * BAR_RATIO) / 2
        centre = x(start) + day_width / 2
        left, right = centre - half, centre + half
        out.append(
            Polygon(
                (
                    (centre, centre_y - half),
                    (right, centre_y),
                    (centre, centre_y + half),
                    (left, centre_y),
                ),
                row.color,
            )
        )
        side = format_date(start, fmt.language, with_year=with_year)
        if row.remark:
            side += f"  {row.remark}"
    else:
        left, right = x(start), x(end + timedelta(days=1))
        if row.kind == "phase":
            thickness = slot * PHASE_RATIO
            out.append(Rect(left, centre_y - thickness / 2, right - left, thickness, row.color))
            out.append(Line(left, centre_y, left, top + slot, "connector"))
            out.append(Line(right, centre_y, right, top + slot, "connector"))
        else:
            thickness = slot * BAR_RATIO
            out.append(Rect(left, centre_y - thickness / 2, right - left, thickness, row.color))
    if not side:
        return out
    if scale.fraction(end + timedelta(days=1)) <= RIGHT_LIMIT:
        out.append(Text(right + SIDE_GAP, top, SIDE_WIDTH, slot, side, "left", "value"))
    elif scale.fraction(start) >= LEFT_LIMIT or row.kind != "bar":
        out.append(
            Text(left - SIDE_GAP - SIDE_WIDTH, top, SIDE_WIDTH, slot, side, "right", "value")
        )
    else:  # a bar across nearly the whole scale carries its remark inside
        thickness = slot * BAR_RATIO
        out.append(
            Text(
                left,
                centre_y - thickness / 2,
                right - left,
                thickness,
                side,
                "center",
                "value",
                row.color,
            )
        )
    return out


def _header(scale: TimeScale, x: _X, language: str) -> list[Primitive]:
    """Upper units on top, lower units below, a line under them and between the upper units."""
    out: list[Primitive] = []
    upper = scale.periods(scale.upper)
    out.extend(
        Text(
            x(period.start),
            0,
            x(period.end) - x(period.start),
            HEADER_ROW,
            label(period.start, scale.upper, language, upper=True),
            "center",
            "axis",
        )
        for period in upper
        if scale.labelled(period, scale.upper)
    )
    out.extend(
        Line(x(period.start), 0, x(period.start), 2 * HEADER_ROW, "grid") for period in upper[1:]
    )
    out.extend(
        Text(
            x(period.start),
            HEADER_ROW,
            x(period.end) - x(period.start),
            HEADER_ROW,
            label(period.start, scale.lower, language),
            "center",
            "axis",
        )
        for period in scale.periods(scale.lower)
    )
    out.append(Line(x(scale.start), 2 * HEADER_ROW, x(scale.end), 2 * HEADER_ROW, "axis"))
    return out
