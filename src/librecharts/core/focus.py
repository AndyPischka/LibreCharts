"""Focus mode: mute everything that is not part of the chart's message (M22).

A chart can emphasise series, categories or both. The layouts tag their data shapes with a series
and/or category index; :func:`apply` sets ``muted`` on everything outside the focus. The renderer
mixes a muted colour towards the background and keeps text contrast, so the decision stays in
``core`` and is testable without LibreOffice.
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qs

from librecharts.core.model import ChartState, Focus
from librecharts.core.primitives import (
    Bubble,
    Line,
    Marker,
    Polygon,
    Polyline,
    Primitive,
    Rect,
)


def apply(primitives: tuple[Primitive, ...], focus: Focus | None) -> tuple[Primitive, ...]:
    """``primitives`` with ``muted`` set on every data shape outside ``focus``.

    Primitive kinds without a series and category (axis, gridlines, legend) stay as they are.
    """
    if focus is None:
        return primitives
    return tuple(_mute(p, focus) for p in primitives)


def _mute(p: Primitive, focus: Focus) -> Primitive:
    series: int | None = None
    category: int | None = None
    if isinstance(p, Rect):
        series, category = (p.series if p.series >= 0 else None), p.category
    elif isinstance(p, (Polyline, Polygon, Marker, Bubble)):
        series, category = p.series, p.category
    elif isinstance(p, Line):
        category = p.category
    else:  # Text
        category = p.key.category if p.key is not None else None
        if p.key is not None and p.key.series is not None:
            series = p.key.series
        elif p.fill is not None and p.fill >= 0:
            series = p.fill
    if series is None and category is None:
        return p
    if focus.shown(series, category):
        return p
    return replace(p, muted=True)


def changed(state: ChartState, query: str) -> ChartState:
    """``state`` with the focus change in ``query`` applied.

    Accepted forms: ``clear=true`` (or ``focus=none``), ``focus=series&index=2&on=true`` and
    ``focus=category&index=1&on=false``. The plan's command uses ``index``; ``series`` and
    ``categories`` are accepted as aliases for scripts. Invalid arguments raise ``ValueError``.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    if args.get("clear") == "true" or args.get("focus") == "none":
        return replace(state, focus=None)
    kind = args.get("focus")
    if kind not in ("series", "category"):
        raise ValueError("a focus change needs focus=series, focus=category or focus=none")
    index_text = args.get("index", args.get(kind))
    if index_text is None:
        raise ValueError("a focus change needs an index")
    try:
        index = int(index_text)
    except ValueError as exc:
        raise ValueError("a focus index must be a number") from exc
    on = {"true": True, "false": False}.get(args.get("on", "true"))
    if on is None:
        raise ValueError("on must be true or false")
    if index < 0:
        raise ValueError("focus indices must not be negative")
    current_series = state.focus.series if state.focus else ()
    current_categories = state.focus.categories if state.focus else ()
    selected = set(current_series if kind == "series" else current_categories)
    if on:
        selected.add(index)
    else:
        selected.discard(index)
    series = tuple(sorted(selected)) if kind == "series" else current_series
    categories = tuple(sorted(selected)) if kind == "category" else current_categories
    if not series and not categories:
        return replace(state, focus=None)
    return replace(state, focus=Focus(series, categories))


def describe(
    state: ChartState, names: tuple[str, ...] = (), categories: tuple[str, ...] = ()
) -> str:
    """A short human-readable description for menus and the sidebar (empty without focus)."""
    if state.focus is None:
        return ""
    parts: list[str] = []
    if state.focus.series:
        parts.extend(names[i] for i in state.focus.series if i < len(names))
    if state.focus.categories:
        parts.extend(categories[i] for i in state.focus.categories if i < len(categories))
    return ", ".join(parts)
