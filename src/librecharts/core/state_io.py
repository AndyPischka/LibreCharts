"""JSON (de)serialisation of :class:`ChartState` with schema versioning.

The JSON is stored in the document, so it outlives this code: every released schema version must
stay readable. To change the schema, bump ``SCHEMA_VERSION`` and register a migration that upgrades
version N to N + 1 in ``_MIGRATIONS``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from typing import Any, cast

from librecharts.core.model import (
    SCHEMA_VERSION,
    Annotation,
    Calendar,
    ChartState,
    Focus,
    Format,
    LabelKey,
    LabelOffset,
    Link,
    Magnitude,
    MatrixSpec,
    Note,
    TableSpec,
    Trend,
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


def _v11_to_v12(raw: _Raw) -> _Raw:
    """Version 12 added label offsets; no existing chart has moved labels."""
    return {**raw, "labels": []}


def _v12_to_v13(raw: _Raw) -> _Raw:
    """Version 13 added the end series of an arrow and the text of a group bracket.

    An existing arrow keeps measuring its start series at both ends (``series_end`` null), and
    no existing chart has a group bracket to label.
    """
    annotations: list[Any] = []
    for annotation in _as_list(raw.get("annotations", [])):
        annotations.append({**_as_object(annotation), "series_end": None, "text": ""})
    return {**raw, "annotations": annotations}


def _v13_to_v14(raw: _Raw) -> _Raw:
    """Version 14 added floating bars, error bars and the waterfall variants (M15).

    No existing chart uses them, so every flag starts false.
    """
    return {**raw, "range": False, "errors": False, "horizontal": False, "stacked": False}


def _v14_to_v15(raw: _Raw) -> _Raw:
    """Version 15 added the working-day calendar of Gantt charts (M17).

    Existing charts keep every day working, so their time scale stays linear.
    """
    return {
        **raw,
        "calendar": {"working_days": [0, 1, 2, 3, 4, 5, 6], "holidays": []},
    }


def _v15_to_v16(raw: _Raw) -> _Raw:
    """Version 16 added patterns beside the colours (M20); existing charts stay plain colour."""
    return {**raw, "format": {**_as_object(raw.get("format", {})), "patterns": False}}


def _v16_to_v17(raw: _Raw) -> _Raw:
    """Version 17 added label overrides, focus, source and notes, and the format's font size and
    legend position (M22).

    Existing labels keep their offset and stay visible with the layout's text; a chart has no
    focus, source or notes, uses the scheme font and the top legend band.
    """
    labels: list[Any] = []
    for label in _as_list(raw.get("labels", [])):
        labels.append({**_as_object(label), "hidden": False, "text": ""})
    return {
        **raw,
        "labels": labels,
        "focus": None,
        "notes": [],
        "source": "",
        "format": {
            **_as_object(raw.get("format", {})),
            "font_size": None,
            "legend": "top",
        },
    }


def _v17_to_v18(raw: _Raw) -> _Raw:
    """Version 18 added manual axes, axis titles and trendlines (M23)."""
    return {
        **raw,
        "trends": [],
        "format": {
            **_as_object(raw.get("format", {})),
            "axis_min": None,
            "axis_max": None,
            "axis_step": None,
            "axis_scale": "linear",
            "axis_title": "",
            "category_axis_title": "",
        },
    }


def _v18_to_v19(raw: _Raw) -> _Raw:
    """Version 19 added the comparison charts and the Pareto switch (M24)."""
    return {**raw, "pareto": False}


def _v19_to_v20(raw: _Raw) -> _Raw:
    """Version 20 added table and matrix charts (M25); no old chart has their specs."""
    return {**raw, "table": None, "matrix": None}


def _v20_to_v21(raw: _Raw) -> _Raw:
    """Version 21 added the auto-update flag of data links (M28)."""
    link = raw.get("link")
    if isinstance(link, dict):
        entry = cast("_Raw", link)
        return {**raw, "link": {**entry, "auto": False}}
    return raw


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
    11: _v11_to_v12,
    12: _v12_to_v13,
    13: _v13_to_v14,
    14: _v14_to_v15,
    15: _v15_to_v16,
    16: _v16_to_v17,
    17: _v17_to_v18,
    18: _v18_to_v19,
    19: _v19_to_v20,
    20: _v20_to_v21,
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
            "calendar": _calendar_to_raw(state.calendar),
            "lines": list(state.lines),
            "secondary": list(state.secondary),
            "colors": list(state.colors),
            "scale_group": state.scale_group,
            "doughnut": state.doughnut,
            "link": None if state.link is None else _link_to_raw(state.link),
            "labels": [_label_to_raw(offset) for offset in state.labels],
            "range": state.range,
            "errors": state.errors,
            "horizontal": state.horizontal,
            "stacked": state.stacked,
            "focus": None if state.focus is None else _focus_to_raw(state.focus),
            "notes": [_note_to_raw(note) for note in state.notes],
            "source": state.source,
            "trends": [_trend_to_raw(trend) for trend in state.trends],
            "pareto": state.pareto,
            "table": None if state.table is None else _table_to_raw(state.table),
            "matrix": None if state.matrix is None else _matrix_to_raw(state.matrix),
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
            calendar=_as_calendar(_get(raw, "calendar")),
            lines=_as_indices(_get(raw, "lines"), "line series"),
            secondary=_as_indices(_get(raw, "secondary"), "secondary series"),
            colors=_as_colors(_get(raw, "colors")),
            scale_group=_as_optional_text(_get(raw, "scale_group")),
            doughnut=_as_flag(_get(raw, "doughnut"), "doughnut"),
            link=_as_link(_get(raw, "link")),
            labels=tuple(_as_label(item) for item in _as_labels(_get(raw, "labels"))),
            range=_as_flag(_get(raw, "range"), "range"),
            errors=_as_flag(_get(raw, "errors"), "errors"),
            horizontal=_as_flag(_get(raw, "horizontal"), "horizontal"),
            stacked=_as_flag(_get(raw, "stacked"), "stacked"),
            focus=_as_focus(_get(raw, "focus")),
            notes=tuple(_as_note(item) for item in _as_array(_get(raw, "notes"), "notes")),
            source=_as_text(_get(raw, "source"), "the source"),
            trends=tuple(_as_trend(item) for item in _as_array(_get(raw, "trends"), "trends")),
            pareto=_as_flag(_get(raw, "pareto"), "pareto"),
            table=_as_table(_get(raw, "table")),
            matrix=_as_matrix(_get(raw, "matrix")),
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
        "series_end": annotation.series_end,
        "text": annotation.text,
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
        "patterns": fmt.patterns,
        "font_size": fmt.font_size,
        "legend": fmt.legend,
        "axis_min": fmt.axis_min,
        "axis_max": fmt.axis_max,
        "axis_step": fmt.axis_step,
        "axis_scale": fmt.axis_scale,
        "axis_title": fmt.axis_title,
        "category_axis_title": fmt.category_axis_title,
    }


def _calendar_to_raw(calendar: Calendar) -> _Raw:
    return {
        "working_days": list(calendar.working_days),
        "holidays": [day.isoformat() for day in calendar.holidays],
    }


def _link_to_raw(link: Link) -> _Raw:
    return {
        "url": link.url,
        "relative": link.relative,
        "sheet": link.sheet,
        "range": link.range,
        "updated": link.updated,
        "modified": link.modified,
        "auto": link.auto,
    }


def _label_to_raw(offset: LabelOffset) -> _Raw:
    return {
        "role": offset.key.role,
        "category": offset.key.category,
        "series": offset.key.series,
        "dx": offset.dx,
        "dy": offset.dy,
        "hidden": offset.hidden,
        "text": offset.text,
    }


def _focus_to_raw(focus: Focus) -> _Raw:
    return {"series": list(focus.series), "categories": list(focus.categories)}


def _note_to_raw(note: Note) -> _Raw:
    return {"text": note.text, "x": note.x, "y": note.y}


def _table_to_raw(table: TableSpec) -> _Raw:
    return {
        "header": table.header,
        "first_column": table.first_column,
        "zebra": table.zebra,
        "borders": table.borders,
        "heatmap": table.heatmap,
        "widths": list(table.widths),
        "row_height": table.row_height,
    }


def _matrix_to_raw(matrix: MatrixSpec) -> _Raw:
    return {
        "x_title": matrix.x_title,
        "y_title": matrix.y_title,
        "x_low": matrix.x_low,
        "x_high": matrix.x_high,
        "y_low": matrix.y_low,
        "y_high": matrix.y_high,
        "quadrants": list(matrix.quadrants),
        "x_split": matrix.x_split,
        "y_split": matrix.y_split,
        "bubbles": matrix.bubbles,
        "labels": matrix.labels,
    }


def _trend_to_raw(trend: Trend) -> _Raw:
    return {
        "series": trend.series,
        "kind": trend.kind,
        "forecast": trend.forecast,
        "show_r2": trend.show_r2,
        "show_equation": trend.show_equation,
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
    series, series_end = _get(raw, "series"), _get(raw, "series_end")
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
        series_end=None if series_end is None else _as_index(series_end),
        text=_as_text(_get(raw, "text"), "the bracket label"),
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
        patterns=_as_flag(_get(raw, "patterns"), "patterns"),
        font_size=_as_number(_get(raw, "font_size")),
        legend=_get(raw, "legend"),
        axis_min=_as_number(_get(raw, "axis_min")),
        axis_max=_as_number(_get(raw, "axis_max")),
        axis_step=_as_number(_get(raw, "axis_step")),
        axis_scale=_get(raw, "axis_scale"),
        axis_title=_as_text(_get(raw, "axis_title"), "the value-axis title"),
        category_axis_title=_as_text(_get(raw, "category_axis_title"), "the category-axis title"),
    )


def _as_calendar(value: object) -> Calendar:
    raw = _as_object(value)
    return Calendar(
        working_days=_as_indices(_get(raw, "working_days"), "working days"),
        holidays=tuple(_as_date(day) for day in _as_array(_get(raw, "holidays"), "holidays")),
    )


def _as_date(value: object) -> date:
    if not isinstance(value, str):
        raise StateError("holidays must be ISO dates")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise StateError(f"invalid holiday date: {value!r}") from exc


def _as_array(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise StateError(f"{name} must be a list")
    return cast("list[object]", value)


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


def _as_labels(value: object) -> list[object]:
    if not isinstance(value, list):
        raise StateError("labels must be a list")
    return cast("list[object]", value)


def _as_label(value: object) -> LabelOffset:
    raw = _as_object(value)
    series = _get(raw, "series")
    dx, dy = _as_number(_get(raw, "dx")), _as_number(_get(raw, "dy"))
    if dx is None or dy is None:
        raise StateError("label offsets must be numbers")
    return LabelOffset(
        LabelKey(
            role=_get(raw, "role"),
            category=_as_index(_get(raw, "category"), "label indices"),
            series=None if series is None else _as_index(series, "label indices"),
        ),
        dx,
        dy,
        hidden=_as_flag(_get(raw, "hidden"), "hidden"),
        text=_as_text(_get(raw, "text"), "the label text"),
    )


def _as_focus(value: object) -> Focus | None:
    if value is None:
        return None
    raw = _as_object(value)
    return Focus(
        series=_as_indices(_get(raw, "series"), "focus series"),
        categories=_as_indices(_get(raw, "categories"), "focus categories"),
    )


def _as_note(value: object) -> Note:
    raw = _as_object(value)
    x, y = _as_number(_get(raw, "x")), _as_number(_get(raw, "y"))
    if x is None or y is None:
        raise StateError("note positions must be numbers")
    return Note(_as_text(_get(raw, "text"), "the note text"), x, y)


def _as_table(value: object) -> TableSpec | None:
    if value is None:
        return None
    raw = _as_object(value)
    widths = _as_array(_get(raw, "widths"), "column widths")
    return TableSpec(
        header=_as_flag(_get(raw, "header"), "header"),
        first_column=_as_flag(_get(raw, "first_column"), "first_column"),
        zebra=_as_flag(_get(raw, "zebra"), "zebra"),
        borders=_as_flag(_get(raw, "borders"), "borders"),
        heatmap=_as_flag(_get(raw, "heatmap"), "heatmap"),
        widths=tuple(_as_number(width) or 0.0 for width in widths),
        row_height=_as_number(_get(raw, "row_height")),
    )


def _as_matrix(value: object) -> MatrixSpec | None:
    if value is None:
        return None
    raw = _as_object(value)
    quadrants = _as_array(_get(raw, "quadrants"), "quadrant labels")
    if len(quadrants) != 4:
        raise StateError("a matrix has four quadrant labels")
    return MatrixSpec(
        x_title=_as_text(_get(raw, "x_title"), "the x title"),
        y_title=_as_text(_get(raw, "y_title"), "the y title"),
        x_low=_as_text(_get(raw, "x_low"), "the x low label"),
        x_high=_as_text(_get(raw, "x_high"), "the x high label"),
        y_low=_as_text(_get(raw, "y_low"), "the y low label"),
        y_high=_as_text(_get(raw, "y_high"), "the y high label"),
        quadrants=cast(
            "tuple[str, str, str, str]",
            tuple(_as_text(item, "a quadrant label") for item in quadrants),
        ),
        x_split=_as_number(_get(raw, "x_split")),
        y_split=_as_number(_get(raw, "y_split")),
        bubbles=_as_flag(_get(raw, "bubbles"), "bubbles"),
        labels=_as_flag(_get(raw, "labels"), "labels"),
    )


def _as_trend(value: object) -> Trend:
    raw = _as_object(value)
    return Trend(
        series=_as_index(_get(raw, "series"), "trend series"),
        kind=_get(raw, "kind"),
        forecast=_as_index(_get(raw, "forecast"), "the forecast"),
        show_r2=_as_flag(_get(raw, "show_r2"), "show_r2"),
        show_equation=_as_flag(_get(raw, "show_equation"), "show_equation"),
    )


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
        auto=_as_flag(_get(raw, "auto"), "auto"),
    )


def _as_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise StateError(f"{name} must be a string")
    return value
