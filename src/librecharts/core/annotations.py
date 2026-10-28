"""Values and labels of annotations (difference and CAGR arrows, axis breaks).

Which annotation kinds a chart kind supports, and the text an arrow shows. Labels are
locale-neutral like the value labels ("+25%", "-2.5"); an en dash marks a value that cannot be
computed.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from librecharts.core.datasheet import ChartData
from librecharts.core.model import Annotation, ChartKind

NOT_AVAILABLE = "\u2013"  # en dash

# Annotation kinds per chart kind; bar and waterfall charts follow later (M4 plan).
SUPPORTED: dict[ChartKind, frozenset[str]] = {
    "column": frozenset({"difference", "cagr"}),
}


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
    return annotation.series is None or annotation.series < len(data.series)


def measured_value(data: ChartData, category: int, series: int | None) -> float | None:
    """The value an arrow end measures: one series' value, or the column total for ``None``."""
    if series is not None:
        return data.series[series].values[category]
    values = [v for s in data.series if (v := s.values[category]) is not None]
    return sum(values) if values else None


def label(annotation: Annotation, data: ChartData) -> str:
    """The text shown on an arrow. A CAGR always runs from the earlier to the later category."""
    first, last = annotation.start, annotation.end
    if annotation.kind == "cagr":
        first, last = sorted((first, last))
    start = measured_value(data, first, annotation.series)
    end = measured_value(data, last, annotation.series)
    if start is None or end is None:
        return NOT_AVAILABLE
    if annotation.kind == "cagr":
        return "CAGR " + _cagr(start, end, _periods(data, annotation))
    if annotation.label == "absolute":
        return _signed(end - start, decimals=2)
    if start == 0:
        return NOT_AVAILABLE
    return _signed((end - start) / abs(start) * 100, decimals=1) + "%"


def _periods(data: ChartData, annotation: Annotation) -> int:
    """Years between the two categories if both are named by whole numbers, else their distance."""
    first, last = sorted((annotation.start, annotation.end))
    try:
        years = int(data.categories[last]) - int(data.categories[first])
    except ValueError:
        years = 0
    return years if years > 0 else last - first


def _cagr(start: float, end: float, periods: int) -> str:
    if start <= 0 or end < 0:
        return NOT_AVAILABLE
    return _signed(((end / start) ** (1 / periods) - 1) * 100, decimals=1) + "%"


def _signed(value: float, decimals: int) -> str:
    text = f"{value:+.{decimals}f}".rstrip("0").rstrip(".")
    return "0" if text in ("+0", "-0") else text


def from_query(query: str) -> Annotation:
    """Parse command arguments like ``kind=difference&start=0&end=2&label=absolute``.

    Raises ``ValueError`` for missing or invalid arguments.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    try:
        kind, start = args["kind"], int(args["start"])
    except KeyError as exc:
        raise ValueError(f"missing argument {exc}") from exc
    series = args.get("series")
    return Annotation(
        kind=kind,  # pyright: ignore[reportArgumentType]  # validated by Annotation
        start=start,
        end=int(args.get("end", start)),
        series=None if series is None else int(series),
        style=args.get("style", "bracket"),  # pyright: ignore[reportArgumentType]
        label=args.get("label", "percent"),  # pyright: ignore[reportArgumentType]
    )
