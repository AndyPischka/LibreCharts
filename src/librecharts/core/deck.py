"""Deck specification: build a presentation's charts from one JSON file (M18, ADR 0028).

A template presentation carries placeholder shapes named ``librecharts-placeholder:<key>``; a JSON
file describes one chart per placeholder. Everything here is parsing and validation, so a bad
specification fails before anything is drawn. ``lo/deck.py`` finds the placeholders and inserts the
charts. Pure Python, no UNO.

The file looks like this::

    {
      "version": 1,
      "charts": [
        {
          "placeholder": "revenue",
          "kind": "column",
          "data": [[null, "2023", "2024"], ["Product A", 10, 12]]
        }
      ]
    }

``data`` is a data sheet grid (first row category names, first column series names), not a Calc
range: a chart built this way needs no data sheet window.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, cast, get_args

from librecharts.core import format as formats
from librecharts.core import links
from librecharts.core.datasheet import Cell, state_from_table
from librecharts.core.messages import text
from librecharts.core.model import Calendar, ChartKind, ChartState, Grouping

VERSION = 1
MAX_CELLS = links.MAX_CELLS  # a larger grid is almost certainly a mistake
PLACEHOLDER_PREFIX = "librecharts-placeholder:"

_DECK_KEYS = frozenset({"version", "charts"})
_CHART_KEYS = frozenset(
    {
        "placeholder",
        "kind",
        "grouping",
        "data",
        "percent",
        "sort",
        "doughnut",
        "range",
        "errors",
        "horizontal",
        "stacked",
        "lines",
        "secondary",
        "colors",
        "format",
        "calendar",
    }
)
_FLAGS = ("percent", "doughnut", "range", "errors", "horizontal", "stacked")
_INDICES = ("lines", "secondary")
_CALENDAR_KEYS = frozenset({"working_days", "holidays"})


class DeckError(ValueError):
    """A deck specification that cannot be used; ``key`` is the message key of the reason."""

    def __init__(self, key: str, detail: str = "", placeholder: str = "") -> None:
        super().__init__(key)
        self.key, self.detail, self.placeholder = key, detail, placeholder

    def message(self, locale: str) -> str:
        """The reason as shown to the user, in ``locale``."""
        return text(self.key, locale, detail=self.detail, placeholder=self.placeholder)


@dataclass(frozen=True, slots=True)
class ChartSpec:
    """One chart of a deck: the placeholder it belongs to and what to draw there."""

    placeholder: str
    state: ChartState


@dataclass(frozen=True, slots=True)
class Deck:
    """A parsed deck specification: one chart per placeholder, in file order."""

    charts: tuple[ChartSpec, ...]


def parse(text_: str, locale: str = "") -> Deck:
    """Parse a deck specification; raises ``DeckError`` for anything unusable."""
    try:
        raw: object = json.loads(text_, parse_constant=_reject_constant)
    except ValueError as exc:  # json.JSONDecodeError included
        raise DeckError("deck_bad_json", str(exc)) from exc
    if not isinstance(raw, dict):
        raise DeckError("deck_bad_spec")
    deck = cast("dict[str, Any]", raw)
    _unknown(deck, _DECK_KEYS)
    version = deck.get("version", VERSION)
    if version != VERSION:
        raise DeckError("deck_bad_version", _shown(version))
    entries = deck.get("charts")
    if not isinstance(entries, list) or not entries:
        raise DeckError("deck_no_charts")
    charts: list[ChartSpec] = []
    seen: set[str] = set()
    for entry in cast("list[Any]", entries):
        if not isinstance(entry, dict):
            raise DeckError("deck_bad_chart")
        chart = chart_spec(cast("dict[str, Any]", entry), locale)
        if chart.placeholder in seen:
            raise DeckError("deck_duplicate_placeholder", chart.placeholder)
        seen.add(chart.placeholder)
        charts.append(chart)
    return Deck(tuple(charts))


def parse_chart(text_: str, locale: str = "") -> ChartSpec:
    """One chart object of the specification, e.g. to insert a single chart into a slide.

    ``placeholder`` is optional here: it only matters when filling a template.
    """
    raw = _json_object(text_)
    _unknown(raw, _CHART_KEYS)
    placeholder = raw.get("placeholder", "")
    if not isinstance(placeholder, str):
        raise DeckError("deck_no_placeholder")
    return ChartSpec(placeholder.strip(), chart_state(raw, locale))


def chart_spec(raw: Mapping[str, Any], locale: str = "") -> ChartSpec:
    """The chart ``raw`` describes: its placeholder and its state."""
    _unknown(raw, _CHART_KEYS)
    placeholder = raw.get("placeholder")
    if not isinstance(placeholder, str) or not placeholder.strip():
        raise DeckError("deck_no_placeholder")
    placeholder = placeholder.strip()
    try:
        state = chart_state(raw, locale)
    except DeckError as exc:  # name the chart the problem belongs to
        raise DeckError(exc.key, exc.detail, placeholder) from exc
    return ChartSpec(placeholder, state)


def _json_object(text_: str) -> dict[str, Any]:
    """The JSON object in ``text_``; raises ``DeckError`` for malformed or non-object input."""
    try:
        raw: object = json.loads(text_, parse_constant=_reject_constant)
    except ValueError as exc:  # json.JSONDecodeError included
        raise DeckError("deck_bad_json", str(exc)) from exc
    if not isinstance(raw, dict):
        raise DeckError("deck_bad_chart")
    return cast("dict[str, Any]", raw)


def chart_state(raw: Mapping[str, Any], locale: str = "") -> ChartState:
    """The ``ChartState`` of one chart of the specification.

    ``locale`` fills in the defaults a chart inserted from the menu gets: the decimal separator
    and the language of magnitude suffixes. Options the specification leaves out keep those
    defaults; every ``ChartState`` field a user can set is allowed.
    """
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in get_args(ChartKind):
        raise DeckError("deck_bad_kind", _shown(kind))
    grouping = raw.get("grouping", "stacked")
    if not isinstance(grouping, str):
        raise DeckError("deck_invalid_chart", _shown(grouping))
    kind_value, grouping_value = cast("ChartKind", kind), cast("Grouping", grouping)
    options: dict[str, Any] = {"format": formats.default_format(kind, grouping_value, locale)}
    if "format" in raw:
        options["format"] = _format(raw["format"], options["format"])
    for key in _FLAGS:
        if key in raw:
            options[key] = _flag(key, raw[key])
    if "sort" in raw:
        options["sort"] = _sort(raw["sort"])
    for key in _INDICES:
        if key in raw:
            options[key] = _indices(key, raw[key])
    if "colors" in raw:
        options["colors"] = _colors(raw["colors"])
    if "calendar" in raw:
        options["calendar"] = _calendar(raw["calendar"])
    table = _table(raw.get("data"))
    try:
        state = state_from_table(kind_value, grouping_value, table)
        return replace(state, **options)
    except (TypeError, ValueError) as exc:
        raise DeckError("deck_invalid_chart", str(exc)) from exc


def _format(value: object, base: formats.Format) -> formats.Format:
    if not isinstance(value, dict):
        raise DeckError("deck_invalid_chart", _shown(value))
    try:
        return formats.from_mapping(cast("dict[str, Any]", value), base)
    except (TypeError, ValueError) as exc:
        raise DeckError("deck_invalid_chart", str(exc)) from exc


def _table(value: object) -> tuple[tuple[Cell, ...], ...]:
    """The data grid of a chart: at least 2 x 2 cells, rectangular, numbers, text or ``null``."""
    rows_value = _list(value, "deck_bad_data")
    if len(rows_value) < 2:
        raise DeckError("deck_bad_data")
    rows: list[tuple[Cell, ...]] = []
    width = 0
    for row in rows_value:
        cells = _list(row, "deck_bad_data")
        if len(cells) < 2 or (width and len(cells) != width):
            raise DeckError("deck_bad_data")
        width = len(cells)
        rows.append(tuple(_cell(cell) for cell in cells))
    if len(rows) * width > MAX_CELLS:
        raise DeckError("deck_too_large", str(MAX_CELLS))
    return tuple(rows)


def _list(value: object, key: str) -> list[Any]:
    """``value`` as a JSON array, or ``DeckError(key)``."""
    if not isinstance(value, list):
        raise DeckError(key)
    return cast("list[Any]", value)


def _cell(value: object) -> Cell:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):  # a boolean is not a data sheet value
        raise DeckError("deck_bad_data")
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise DeckError("deck_bad_data")
        return number
    raise DeckError("deck_bad_data")


def _flag(key: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise DeckError("deck_invalid_chart", f"{key}: {_shown(value)}")
    return value


def _sort(value: object) -> str:
    if not isinstance(value, str):
        raise DeckError("deck_invalid_chart", f"sort: {_shown(value)}")
    return value


def _indices(key: str, value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise DeckError("deck_invalid_chart", f"{key}: {_shown(value)}")
    items = cast("list[Any]", value)
    found: list[int] = []
    for index in items:
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise DeckError("deck_invalid_chart", f"{key}: {_shown(items)}")
        found.append(index)
    return tuple(found)


def _colors(value: object) -> tuple[int | None, ...]:
    if not isinstance(value, list):
        raise DeckError("deck_invalid_chart", f"colors: {_shown(value)}")
    items = cast("list[Any]", value)
    found: list[int | None] = []
    for colour in items:
        if colour is None:
            found.append(None)
        elif isinstance(colour, int) and not isinstance(colour, bool) and colour >= 0:
            found.append(colour)
        else:
            raise DeckError("deck_invalid_chart", f"colors: {_shown(items)}")
    return tuple(found)


def _calendar(value: object) -> Calendar:
    if not isinstance(value, dict):
        raise DeckError("deck_bad_calendar", _shown(value))
    raw = cast("dict[str, Any]", value)
    _unknown(raw, _CALENDAR_KEYS)
    days = _list(raw.get("working_days", [0, 1, 2, 3, 4, 5, 6]), "deck_bad_calendar")
    holidays = _list(raw.get("holidays", []), "deck_bad_calendar")
    if any(not isinstance(day, int) or isinstance(day, bool) for day in days):
        raise DeckError("deck_bad_calendar", _shown(raw))
    if any(not isinstance(day, str) for day in holidays):
        raise DeckError("deck_bad_calendar", _shown(raw))
    try:
        return Calendar(
            tuple(cast("list[int]", days)),
            tuple(date.fromisoformat(cast("str", day)) for day in holidays),
        )
    except ValueError as exc:  # no working day at all, or a date Calc cannot read
        raise DeckError("deck_bad_calendar", str(exc)) from exc


def _unknown(raw: Mapping[str, Any], allowed: frozenset[str]) -> None:
    """Reject keys the specification does not know: a typo must not pass silently."""
    for key in raw:
        if key not in allowed:
            raise DeckError("deck_unknown_key", key)


def _shown(value: object) -> str:
    """``value`` as named in a message: strings unchanged, anything else as JSON."""
    if isinstance(value, str):
        return value or '""'
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return str(value)


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not a number")  # NaN and Infinity are no data sheet values


# Placeholder shapes.


def placeholder_name(key: str) -> str:
    """The shape name that marks where the chart of ``key`` goes."""
    return PLACEHOLDER_PREFIX + key


def placeholder_key(name: str) -> str | None:
    """The key of a placeholder shape name, or ``None`` if ``name`` is no placeholder."""
    if not name.startswith(PLACEHOLDER_PREFIX):
        return None
    return name[len(PLACEHOLDER_PREFIX) :].strip() or None


# Reports.


def unused_report(keys: Sequence[str], locale: str) -> str:
    """Which placeholders stayed empty, or ``""`` if none did.

    A template may carry sections not every deck uses, so an empty placeholder is no error.
    """
    if not keys:
        return ""
    return text("deck_unused_placeholders", locale, detail=", ".join(sorted(keys)))


def built_report(count: int, file_name: str, locale: str) -> str:
    """What to tell the user after a build."""
    if count == 1:
        return text("deck_built_one", locale, file=file_name)
    return text("deck_built", locale, count=str(count), file=file_name)
