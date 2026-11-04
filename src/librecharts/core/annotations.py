"""Values and labels of annotations (difference and CAGR arrows, axis breaks, value lines,
category gaps, group brackets).

Which annotation kinds a chart kind supports, and the text an arrow shows. Labels are
locale-neutral like the value labels ("+25%", "-2.5"); an en dash marks a value that cannot be
computed.
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qs

from librecharts.core.datasheet import ChartData, errored, parse, ranged
from librecharts.core.gantt import parse_gantt, starts
from librecharts.core.mekko import levels as mekko_levels
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import AXIS_ANNOTATIONS, Annotation, ChartKind, ChartState
from librecharts.core.percent import shares
from librecharts.core.scatter import levels as scatter_levels
from librecharts.core.scatter import parse_scatter
from librecharts.core.waterfall import levels, parse_waterfall

NOT_AVAILABLE = "\u2013"  # en dash

# The kinds that connect two points of the chart: (category, series) each.
ARROW_KINDS = frozenset({"difference", "cagr"})

# Annotation kinds per chart kind. A percent chart hides most of them (``picking.supports``),
# except the difference arrows of a percent Mekko, whose segment levels are percentage points.
SUPPORTED: dict[ChartKind, frozenset[str]] = {
    "column": frozenset(
        {"difference", "cagr", "axis_break", "value_line", "category_gap", "group_bracket"}
    ),
    "bar": frozenset(
        {"difference", "cagr", "axis_break", "value_line", "category_gap", "group_bracket"}
    ),
    "waterfall": frozenset({"difference", "cagr", "axis_break", "value_line"}),
    "line": frozenset({"difference", "cagr", "axis_break", "value_line"}),
    "mekko": frozenset({"difference", "cagr"}),
    "pie": frozenset({"difference", "cagr"}),
    "area": frozenset({"value_line"}),
    "scatter": frozenset({"difference", "cagr", "value_line"}),
    "gantt": frozenset({"value_line"}),  # date lines
}


def measured(state: ChartState) -> ChartData:
    """The data an annotation of ``state`` measures: categories and the series values.

    For a waterfall chart one value per step: the level its column ends at; for a Mekko chart
    the segment values (their shares of the column in percent on a percent Mekko, so an absolute
    difference reads as percentage points); for a pie chart the segments' shares of their pie in
    percent, so a difference reads as percentage points; for a scatter chart one y value per
    point; for a Gantt chart one row per category and its start serial number.
    """
    if state.kind == "waterfall":
        return levels(parse_waterfall(state))
    if state.kind == "mekko":
        return mekko_levels(parse_mekko(state), state.percent)
    if state.kind == "pie":
        return shares(parse(state))
    if state.kind == "scatter":
        return scatter_levels(parse_scatter(state))
    if state.kind == "gantt":
        return starts(parse_gantt(state, state.sort))
    if state.range:
        return ranged(state)[0]  # a floating bar is measured at its to level
    if state.errors:
        return errored(state)[0]  # error bars do not change the measured values
    return parse(state)


def arrows(
    annotations: tuple[Annotation, ...], data: ChartData, kind: ChartKind
) -> tuple[list[Annotation], list[Annotation]]:
    """The drawable arrows: (bracket arrows, level arrows). Other annotations are not arrows."""
    shown = [a for a in annotations if a.kind in ARROW_KINDS and drawable(a, data, kind)]
    levels = [a for a in shown if a.kind == "difference" and a.style == "level"]
    return [a for a in shown if a not in levels], levels


def category_gaps(
    annotations: tuple[Annotation, ...], data: ChartData, kind: ChartKind
) -> list[Annotation]:
    """The drawable category gaps of a chart, in the order they were added."""
    return [a for a in annotations if a.kind == "category_gap" and drawable(a, data, kind)]


def group_brackets(
    annotations: tuple[Annotation, ...], data: ChartData, kind: ChartKind
) -> list[Annotation]:
    """The drawable group brackets of a chart, in the order they were added."""
    return [a for a in annotations if a.kind == "group_bracket" and drawable(a, data, kind)]


def value_lines(
    annotations: tuple[Annotation, ...], data: ChartData, kind: ChartKind
) -> list[Annotation]:
    """The drawable value lines of a chart, in the order they were added."""
    return [
        a
        for a in annotations
        if a.kind == "value_line" and drawable(a, data, kind) and data.categories
    ]


def drawable(annotation: Annotation, data: ChartData, kind: ChartKind) -> bool:
    """Whether ``annotation`` can be drawn on ``data``: kind supported and indices in range.

    Annotations pointing past the data (after the user removed a category) are kept in the
    state but not drawn, so undoing the data edit brings them back.
    """
    if annotation.kind not in SUPPORTED.get(kind, frozenset()):
        return False
    count = len(data.categories)
    if annotation.start >= count or annotation.end >= count:
        return False
    return all(
        series is None or series < len(data.series)
        for series in (annotation.series, annotation.series_end)
    )


def measured_value(data: ChartData, category: int, series: int | None) -> float | None:
    """The value an arrow end measures: one series' value, or the column total for ``None``."""
    if series is not None:
        return data.series[series].values[category]
    values = [v for s in data.series if (v := s.values[category]) is not None]
    return sum(values) if values else None


def label(annotation: Annotation, data: ChartData, x: tuple[float, ...] | None = None) -> str:
    """The text shown on an arrow. A CAGR always runs from the earlier to the later category.

    ``x``: the x values of a scatter chart's points; a CAGR there counts their distance, not the
    category names. Each end of the arrow measures its own series (``series``/``series_end``), so
    a between-series arrow compares two series of one category.
    """
    start_series, end_series = annotation.series, annotation.series_end
    if end_series is None:
        end_series = start_series  # ``None``: the end measures the start's series (or the total)
    first, last = (annotation.start, start_series), (annotation.end, end_series)
    if annotation.kind == "cagr" and annotation.start > annotation.end:
        first, last = last, first
    start = measured_value(data, *first)
    end = measured_value(data, *last)
    if start is None or end is None:
        return NOT_AVAILABLE
    if annotation.kind == "cagr":
        return "CAGR " + _cagr(start, end, _periods(data, annotation, x))
    if annotation.label == "absolute":
        return _signed(end - start, decimals=2)
    if start == 0:
        return NOT_AVAILABLE
    return _signed((end - start) / abs(start) * 100, decimals=1) + "%"


def _periods(data: ChartData, annotation: Annotation, x: tuple[float, ...] | None = None) -> float:
    """The periods of a CAGR: the x distance of the two points of a scatter chart, else the years
    between the two categories if both are named by whole numbers, else their distance."""
    first, last = sorted((annotation.start, annotation.end))
    if x is not None:
        distance = x[last] - x[first]
        return distance if distance > 0 else float(last - first)
    try:
        years = int(data.categories[last]) - int(data.categories[first])
    except ValueError:
        years = 0
    return years if years > 0 else float(last - first)


def _cagr(start: float, end: float, periods: float) -> str:
    if start <= 0 or end < 0 or periods <= 0:
        return NOT_AVAILABLE
    return _signed(((end / start) ** (1 / periods) - 1) * 100, decimals=1) + "%"


def _signed(value: float, decimals: int) -> str:
    text = f"{value:+.{decimals}f}".rstrip("0").rstrip(".")
    return "0" if text in ("+0", "-0") else text


def added(annotations: tuple[Annotation, ...], new: Annotation) -> tuple[Annotation, ...]:
    """``annotations`` plus ``new``; a chart has one axis break, a new one replaces the old."""
    if new.kind == "axis_break":
        annotations = tuple(a for a in annotations if a.kind != "axis_break")
    return (*annotations, new)


def check_bracket_text(label: str) -> str | None:
    """The message key saying why ``label`` is not a group bracket's text, ``None`` if it is one.

    The dialog keeps its text field open and shows the key's message; the label itself is the
    trimmed field value.
    """
    if not label.strip():
        return "bracket_text_missing"
    if len(label.strip()) > 80:
        return "bracket_text_too_long"
    return None


def changed(annotations: tuple[Annotation, ...], query: str) -> tuple[Annotation, ...]:
    """Apply ``index=1&label=absolute`` (or ``style=...``, ``text=...``, ``lower=..&upper=..``) to
    the annotation at that index; ``lower=&upper=`` (empty) makes an axis break automatic.

    Raises ``ValueError`` for a missing or invalid index or value.
    """
    args = _args(query)
    index = _index(args, annotations)
    old = annotations[index]
    annotation = replace(
        old,
        label=args.get("label", old.label),  # pyright: ignore[reportArgumentType]
        style=args.get("style", old.style),  # pyright: ignore[reportArgumentType]
        lower=_optional_float(args["lower"]) if "lower" in args else old.lower,
        upper=_optional_float(args["upper"]) if "upper" in args else old.upper,
        value=_optional_float(args["value"]) if "value" in args else old.value,
        text=args.get("text", old.text),
    )
    return (*annotations[:index], annotation, *annotations[index + 1 :])


def removed(annotations: tuple[Annotation, ...], query: str) -> tuple[Annotation, ...]:
    """``annotations`` without the one at ``index=...``; ``ValueError`` for a bad index."""
    index = _index(_args(query), annotations)
    return (*annotations[:index], *annotations[index + 1 :])


def _args(query: str) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(query, keep_blank_values=True).items()}


def _index(args: dict[str, str], annotations: tuple[Annotation, ...]) -> int:
    index = int(args.get("index", "-1"))
    if not 0 <= index < len(annotations):
        raise ValueError(f"no annotation {index}")
    return index


def _optional_float(text: str) -> float | None:
    return float(text) if text else None


def from_query(query: str) -> Annotation:
    """Parse command arguments like ``kind=difference&start=0&end=2&label=absolute``.

    An axis break needs no ``start``: ``kind=axis_break`` (automatic) or with
    ``&lower=10&upper=50``. A category gap needs adjacent categories
    (``kind=category_gap&start=1&end=2``), a group bracket a range and may carry its label
    (``kind=group_bracket&start=0&end=2&text=Phase%201``). Raises ``ValueError`` for missing or
    invalid arguments.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    try:
        kind = args["kind"]
        start = int(args.get("start", "0") if kind in AXIS_ANNOTATIONS else args["start"])
    except KeyError as exc:
        raise ValueError(f"missing argument {exc}") from exc
    series = args.get("series")
    series_end = args.get("series_end")
    if series is None and series_end is not None:
        raise ValueError("series_end needs a series")
    return Annotation(
        kind=kind,  # pyright: ignore[reportArgumentType]  # validated by Annotation
        start=start,
        end=int(args.get("end", start)),
        series=None if series is None else int(series),
        style=args.get("style", "bracket"),  # pyright: ignore[reportArgumentType]
        label=args.get("label", "percent"),  # pyright: ignore[reportArgumentType]
        lower=_optional_float(args.get("lower", "")),
        upper=_optional_float(args.get("upper", "")),
        value=_optional_float(args.get("value", "")),
        series_end=None if series_end is None else int(series_end),
        text=args.get("text", ""),
    )
