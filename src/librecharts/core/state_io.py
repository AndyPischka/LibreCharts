"""JSON (de)serialisation of :class:`ChartState` with schema versioning.

The JSON is stored in the document, so it outlives this code: every released schema version must
stay readable. To change the schema, bump ``SCHEMA_VERSION`` and register a migration that upgrades
version N to N + 1 in ``_MIGRATIONS``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from librecharts.core.model import (
    SCHEMA_VERSION,
    Annotation,
    ChartState,
    Format,
    Link,
    Magnitude,
)

_Raw = dict[str, Any]


def _v1_to_v2(raw: _Raw) -> _Raw:
    """Version 2 added annotations."""
    return {**raw, "annotations": []}


def _v2_to_v3(raw: _Raw) -> _Raw:
    """Version 3 gave axis breaks a value range (null: automatic) and made them global."""
    annotations: list[Any] = []
    for annotation in _as_list(raw.get("annotations", [])):
        entry = {**_as_object(annotation), "lower": None, "upper": None}
        if entry.get("kind") == "axis_break":
            entry["start"] = entry["end"] = 0
        annotations.append(entry)
    return {**raw, "annotations": annotations}


def _v3_to_v4(raw: _Raw) -> _Raw:
    """Version 4 added the Mekko option ``percent``; every existing Mekko is a percent Mekko."""
    return {**raw, "percent": raw.get("kind") == "mekko"}


def _v4_to_v5(raw: _Raw) -> _Raw:
    """Version 5 added the category sort order of column and bar charts."""
    return {**raw, "sort": "none"}


def _v5_to_v6(raw: _Raw) -> _Raw:
    """Version 6 added the chart format and value lines.

    Existing column, bar and waterfall charts showed no series names; a Mekko always showed them to
    the right of the last column, so it keeps that look with ``labels``.
    """
    annotations: list[Any] = []
    for annotation in _as_list(raw.get("annotations", [])):
        annotations.append({**_as_object(annotation), "value": None})
    format_raw = {
        "axis": False,
        "gridlines": False,
        "series_names": "labels" if raw.get("kind") == "mekko" else "none",
        "decimals": None,
        "magnitude": 0,
        "unit": "",
        "separator": ".",
        "language": "en",
    }
    return {**raw, "annotations": annotations, "format": format_raw}


def _v6_to_v7(raw: _Raw) -> _Raw:
    """Version 7 added line and area charts, line series and point markers."""
    return {
        **raw,
        "lines": [],
        "secondary": [],
        "format": {**_as_object(raw.get("format", {})), "markers": True},
    }


def _v7_to_v8(raw: _Raw) -> _Raw:
    """Version 8 added per-series palette entries and same-scale groups."""
    return {**raw, "colors": [], "scale_group": None}


def _v8_to_v9(raw: _Raw) -> _Raw:
    """Version 9 added pie (and doughnut), scatter and butterfly charts."""
    return {**raw, "doughnut": False}


def _v9_to_v10(raw: _Raw) -> _Raw:
    """Version 10 added Gantt charts; existing charts need no new field."""
    return raw


def _v10_to_v11(raw: _Raw) -> _Raw:
    """Version 11 added data links; existing charts take their data from the data sheet."""
    return {**raw, "link": None}


# Maps a schema version to the function that upgrades its raw JSON object to the next version.
_MIGRATIONS: dict[int, Callable[[_Raw], _Raw]] = {
    1: _v1_to_v2,
    2: _v2_to_v3,
    3: _v3_to_v4,
    4: _v4_to_v5,
    5: _v5_to_v6,
    6: _v6_to_v7,
    7: _v7_to_v8,
    8: _v8_to_v9,
    9: _v9_to_v10,
    10: _v10_to_v11,
}


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
            "percent": state.percent,
            "sort": state.sort,
            "format": _format_to_raw(state.format),
            "lines": list(state.lines),
            "secondary": list(state.secondary),
            "colors": list(state.colors),
            "scale_group": state.scale_group,
            "doughnut": state.doughnut,
            "link": None if state.link is None else _link_to_raw(state.link),
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
            percent=_as_bool(_get(raw, "percent")),
            sort=_get(raw, "sort"),
            format=_as_format(_get(raw, "format")),
            lines=_as_indices(_get(raw, "lines"), "line series"),
            secondary=_as_indices(_get(raw, "secondary"), "secondary series"),
            colors=_as_colors(_get(raw, "colors")),
            scale_group=_as_optional_text(_get(raw, "scale_group")),
            doughnut=_as_flag(_get(raw, "doughnut"), "doughnut"),
            link=_as_link(_get(raw, "link")),
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
        "lower": annotation.lower,
        "upper": annotation.upper,
        "value": annotation.value,
    }


def _format_to_raw(fmt: Format) -> _Raw:
    return {
        "axis": fmt.axis,
        "gridlines": fmt.gridlines,
        "series_names": fmt.series_names,
        "decimals": fmt.decimals,
        "magnitude": fmt.magnitude,
        "unit": fmt.unit,
        "separator": fmt.separator,
        "language": fmt.language,
        "markers": fmt.markers,
    }


def _link_to_raw(link: Link) -> _Raw:
    return {
        "url": link.url,
        "relative": link.relative,
        "sheet": link.sheet,
        "range": link.range,
        "updated": link.updated,
        "modified": link.modified,
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


def _as_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise StateError("percent must be true or false")
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
        lower=_as_number(_get(raw, "lower")),
        upper=_as_number(_get(raw, "upper")),
        value=_as_number(_get(raw, "value")),
    )


def _as_format(value: object) -> Format:
    raw = _as_object(value)
    return Format(
        axis=_as_flag(_get(raw, "axis"), "axis"),
        gridlines=_as_flag(_get(raw, "gridlines"), "gridlines"),
        series_names=_get(raw, "series_names"),
        decimals=_as_optional_index(_get(raw, "decimals"), "decimals"),
        magnitude=cast("Magnitude", _as_index(_get(raw, "magnitude"))),
        unit=_as_str(_get(raw, "unit")),
        separator=_get(raw, "separator"),
        language=_as_str(_get(raw, "language")),
        markers=_as_flag(_get(raw, "markers"), "markers"),
    )


def _as_flag(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise StateError(f"{name} must be true or false")
    return value


def _as_optional_index(value: object, name: str) -> int | None:
    return None if value is None else _as_index(value, name)


def _as_index(value: object, name: str = "annotation indices") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StateError(f"{name} must be integers")
    return value


def _as_indices(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise StateError(f"{name} must be a list")
    return tuple(_as_index(item, name) for item in cast("list[object]", value))


def _as_colors(value: object) -> tuple[int | None, ...]:
    if not isinstance(value, list):
        raise StateError("colors must be a list")
    return tuple(
        None if item is None else _as_index(item, "palette indices")
        for item in cast("list[object]", value)
    )


def _as_optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StateError("the scale group must be a string or null")
    return value


def _as_link(value: object) -> Link | None:
    if value is None:
        return None
    raw = _as_object(value)
    return Link(
        url=_as_text(_get(raw, "url"), "the link URL"),
        relative=_as_text(_get(raw, "relative"), "the relative link URL"),
        sheet=_as_text(_get(raw, "sheet"), "the linked sheet"),
        range=_as_text(_get(raw, "range"), "the linked range"),
        updated=_as_text(_get(raw, "updated"), "the update time"),
        modified=_as_text(_get(raw, "modified"), "the modification time"),
    )


def _as_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise StateError(f"{name} must be a string")
    return value
