"""JSON (de)serialisation of :class:`ChartState` with schema versioning.

The JSON is stored in the document, so it outlives this code: every released schema version must
stay readable. To change the schema, bump ``SCHEMA_VERSION`` and register a migration that upgrades
version N to N + 1 in ``_MIGRATIONS``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from librecharts.core.model import SCHEMA_VERSION, Annotation, ChartState

_Raw = dict[str, Any]


def _v1_to_v2(raw: _Raw) -> _Raw:
    """Version 2 added annotations."""
    return {**raw, "annotations": []}


# Maps a schema version to the function that upgrades its raw JSON object to the next version.
_MIGRATIONS: dict[int, Callable[[_Raw], _Raw]] = {1: _v1_to_v2}


class StateError(ValueError):
    """The stored chart state is malformed or from an unsupported version."""


def to_json(state: ChartState) -> str:
    return json.dumps(
        {
            "v": state.version,
            "kind": state.kind,
            "grouping": state.grouping,
            "cells": [list(row) for row in state.cells],
            "values": [list(row) for row in state.values],
            "annotations": [_annotation_to_raw(a) for a in state.annotations],
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def from_json(text: str) -> ChartState:
    try:
        data: object = json.loads(text, parse_constant=_reject_constant)
    except ValueError as exc:
        raise StateError(f"invalid JSON: {exc}") from exc
    raw = _migrate(_as_object(data))
    try:
        return ChartState(
            kind=_get(raw, "kind"),
            grouping=_get(raw, "grouping"),
            cells=tuple(tuple(_as_str(c) for c in row) for row in _as_rows(_get(raw, "cells"))),
            values=tuple(
                tuple(_as_number(v) for v in row) for row in _as_rows(_get(raw, "values"))
            ),
            annotations=tuple(_as_annotation(a) for a in _as_list(_get(raw, "annotations"))),
            version=raw["v"],
        )
    except ValueError as exc:
        raise StateError(str(exc)) from exc


def _annotation_to_raw(annotation: Annotation) -> _Raw:
    return {
        "kind": annotation.kind,
        "start": annotation.start,
        "end": annotation.end,
        "series": annotation.series,
        "style": annotation.style,
        "label": annotation.label,
    }


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not valid JSON")


def _migrate(raw: _Raw) -> _Raw:
    version = raw.get("v")
    if isinstance(version, bool) or not isinstance(version, int):
        raise StateError("missing or invalid schema version 'v'")
    if version < 1:
        raise StateError(f"unsupported schema version {version}")
    if version > SCHEMA_VERSION:
        raise StateError(
            f"chart was saved by a newer LibreCharts (schema {version}, supported {SCHEMA_VERSION})"
        )
    while version < SCHEMA_VERSION:
        raw = _MIGRATIONS[version](raw)
        version += 1
        raw["v"] = version
    return raw


def _as_object(value: object) -> _Raw:
    if not isinstance(value, dict):
        raise StateError("chart state must be a JSON object")
    return cast("_Raw", value)


def _get(raw: _Raw, key: str) -> Any:
    if key not in raw:
        raise StateError(f"missing field {key!r}")
    return raw[key]


def _as_rows(value: object) -> list[list[object]]:
    if not isinstance(value, list) or not all(
        isinstance(row, list) for row in cast("list[object]", value)
    ):
        raise StateError("grid must be a list of rows")
    return cast("list[list[object]]", value)


def _as_str(value: object) -> str:
    if not isinstance(value, str):
        raise StateError("cell contents must be strings")
    return value


def _as_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StateError("values must be numbers or null")
    return float(value)


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise StateError("annotations must be a list")
    return cast("list[object]", value)


def _as_annotation(value: object) -> Annotation:
    raw = _as_object(value)
    series = _get(raw, "series")
    return Annotation(
        kind=_get(raw, "kind"),
        start=_as_index(_get(raw, "start")),
        end=_as_index(_get(raw, "end")),
        series=None if series is None else _as_index(series),
        style=_get(raw, "style"),
        label=_get(raw, "label"),
    )


def _as_index(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StateError("annotation indices must be integers")
    return value
