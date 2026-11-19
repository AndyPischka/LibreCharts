"""Alternative text of a chart, generated from its data (M20, ADR 0030).

Screen readers and the PDF/PPTX export read a shape's title and description. Every chart group gets
both: the title names the chart type, the description lists the data in reading order, formatted
like the chart's labels and in the chart's own language. Pure Python, no UNO.
"""

from __future__ import annotations

from librecharts.core.datasheet import parse
from librecharts.core.gantt import parse_gantt
from librecharts.core.layout.common import format_value
from librecharts.core.messages import text
from librecharts.core.model import ChartState, Format
from librecharts.core.scatter import parse_scatter
from librecharts.core.timescale import format_date
from librecharts.core.waterfall import parse_waterfall

MAX_DESCRIPTION = 4000  # characters; a longer description is cut with an ellipsis
ELLIPSIS = "…"


def kind_key(state: ChartState) -> str:
    """The message key suffix naming the chart type and variant (``column_percent``, ``bubble``)."""
    kind = state.kind
    if kind == "mekko" and not state.percent:
        return "mekko_units"
    if kind in ("column", "bar", "area") and state.percent:
        return kind + "_percent"
    if kind == "column" and state.lines:
        return "column_lines"
    if kind == "pie" and state.doughnut:
        return "doughnut"
    if kind == "scatter" and parse_scatter(state).bubbles:
        return "bubble"
    return kind


def title(state: ChartState) -> str:
    """The chart's alternative title: its type, e.g. ``Column chart (100 %)``."""
    return text(f"kind_{kind_key(state)}", state.format.language)


def description(state: ChartState) -> str:
    """The chart's data as sentences, in the chart's language and number format."""
    language = state.format.language
    kind = title(state)
    if state.kind == "waterfall":
        lines = _waterfall(state, kind)
    elif state.kind == "scatter":
        lines = _scatter(state, kind)
    elif state.kind == "gantt":
        lines = _gantt(state, kind)
    else:
        lines = _series(state, kind)
    if lines is None:
        return text("alt_no_data", language, kind=kind)
    return _cut(" ".join(lines))


def _series(state: ChartState, kind: str) -> list[str] | None:
    data = parse(state)
    if not data.categories or not data.series:
        return None
    fmt = state.format
    lines = [
        text(
            "alt_summary",
            fmt.language,
            kind=kind,
            categories=str(len(data.categories)),
            series=str(len(data.series)),
        )
    ]
    for series in data.series:
        values = ", ".join(
            f"{category} = {_value(value, fmt)}"
            for category, value in zip(data.categories, series.values, strict=True)
        )
        lines.append(f"{series.name}: {values}.")
    return lines


def _waterfall(state: ChartState, kind: str) -> list[str] | None:
    steps = parse_waterfall(state).steps
    if not steps:
        return None
    fmt = state.format
    lines = [text("alt_steps", fmt.language, kind=kind, count=str(len(steps)))]
    parts: list[str] = []
    for step in steps:
        if step.is_total:
            parts.append(f"{step.name} = {format_value(step.end, fmt)}")
        elif step.has_value:
            sign = "+" if step.change >= 0 else "-"
            parts.append(f"{step.name} {sign}{format_value(abs(step.change), fmt)}")
        else:
            parts.append(f"{step.name} = {text('alt_empty', fmt.language)}")
    lines.append(", ".join(parts) + ".")
    return lines


def _scatter(state: ChartState, kind: str) -> list[str] | None:
    data = parse_scatter(state)
    if not data.points:
        return None
    fmt = state.format
    lines = [text("alt_points", fmt.language, kind=kind, count=str(len(data.points)))]
    for point in data.points:
        detail = f"x = {format_value(point.x, fmt)}, y = {format_value(point.y, fmt)}"
        if point.size is not None:
            detail += ", " + text("alt_size", fmt.language, size=format_value(point.size, fmt))
        group = data.groups[point.group] if point.group < len(data.groups) else ""
        name = f"{point.label} ({group})" if group and point.label else point.label or group
        lines.append(f"{name}: {detail}." if name else f"{detail}.")
    return lines


def _gantt(state: ChartState, kind: str) -> list[str] | None:
    rows = parse_gantt(state, state.sort).rows
    if not rows:
        return None
    language = state.format.language
    lines = [text("alt_rows", language, kind=kind, count=str(len(rows)))]
    for row in rows:
        marks = [
            text("alt_milestone", language, date=format_date(mark.start, language))
            if mark.kind == "milestone"
            else text(
                "alt_range",
                language,
                start=format_date(mark.start, language),
                end=format_date(mark.end, language),
            )
            for mark in row.marks
        ]
        detail = "; ".join(marks)
        lines.append(f"{row.label}: {detail}." if detail else f"{row.label}.")
    return lines


def _value(value: float | None, fmt: Format) -> str:
    return text("alt_empty", fmt.language) if value is None else format_value(value, fmt)


def _cut(content: str) -> str:
    if len(content) <= MAX_DESCRIPTION:
        return content
    return content[: MAX_DESCRIPTION - 1].rstrip() + ELLIPSIS
