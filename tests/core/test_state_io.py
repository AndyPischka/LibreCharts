import json
from typing import Any

import pytest

from librecharts.core import state_io
from librecharts.core.model import SCHEMA_VERSION, Annotation, ChartState, Format
from librecharts.core.state_io import StateError, from_json, to_json


def make_state(**overrides: Any) -> ChartState:
    fields: dict[str, Any] = {
        "kind": "column",
        "grouping": "stacked",
        "cells": (("", "2024", "2025"), ("Sales", "10", "=B2*2")),
        "values": ((None, None, None), (None, 10.0, 20.0)),
    }
    return ChartState(**{**fields, **overrides})


ARROW = {
    "kind": "difference",
    "start": 0,
    "end": 1,
    "series": None,
    "style": "bracket",
    "label": "percent",
    "lower": None,
    "upper": None,
    "value": None,
}


BREAK = {**ARROW, "kind": "axis_break", "start": 0, "end": 0}


def valid_raw() -> dict[str, Any]:
    return json.loads(to_json(make_state()))


def test_round_trip_preserves_state() -> None:
    state = make_state(grouping="clustered")
    assert from_json(to_json(state)) == state


def test_round_trip_preserves_annotations() -> None:
    annotations = (
        Annotation("difference", 0, 1),
        Annotation("difference", 1, 0, series=2, style="level", label="absolute"),
        Annotation("cagr", 0, 1),
        Annotation("axis_break", 0, 0),
        Annotation("axis_break", 0, 0, lower=10.0, upper=50.5),
    )
    state = make_state(annotations=annotations)
    assert from_json(to_json(state)).annotations == annotations


def test_version_2_annotations_are_migrated_to_automatic_global_axis_breaks() -> None:
    raw = valid_raw()
    old_arrow = {k: v for k, v in ARROW.items() if k not in ("lower", "upper")}
    old_break = {**old_arrow, "kind": "axis_break", "start": 2, "end": 2}
    raw["annotations"] = [old_arrow, old_break]
    raw["v"] = 2
    restored = from_json(json.dumps(raw))
    assert restored.version == SCHEMA_VERSION
    assert restored.annotations == (Annotation("difference", 0, 1), Annotation("axis_break", 0, 0))


def test_round_trip_preserves_the_mekko_variant() -> None:
    for percent in (True, False):
        state = make_state(kind="mekko", percent=percent)
        assert from_json(to_json(state)).percent is percent


def test_round_trip_preserves_the_sort_order() -> None:
    for sort in ("none", "descending", "ascending"):
        assert from_json(to_json(make_state(sort=sort))).sort == sort


def test_round_trip_preserves_the_format() -> None:
    fmt = Format(
        axis=True,
        gridlines=True,
        series_names="legend",
        decimals=3,
        magnitude=6,
        unit="€",
        separator=",",
        language="de",
    )
    assert from_json(to_json(make_state(format=fmt))).format == fmt


def test_a_value_line_round_trips() -> None:
    line = Annotation("value_line", 0, 0, value=12.5)
    average = Annotation("value_line", 0, 0)
    state = make_state(annotations=(line, average))
    assert from_json(to_json(state)).annotations == (line, average)


@pytest.mark.parametrize(
    ("kind", "names"),
    [("column", "none"), ("bar", "none"), ("waterfall", "none"), ("mekko", "labels")],
)
def test_version_5_state_gets_the_default_format(kind: str, names: str) -> None:
    raw = valid_raw()
    del raw["format"]
    raw["kind"] = kind
    raw["annotations"] = [ARROW]
    raw["v"] = 5
    restored = from_json(json.dumps(raw))
    assert restored.version == SCHEMA_VERSION
    assert restored.format == Format(series_names=names)  # pyright: ignore[reportArgumentType]
    assert restored.annotations[0].value is None


def test_version_5_state_survives_without_annotations() -> None:
    raw = valid_raw()
    del raw["format"]
    raw["v"] = 5
    assert from_json(json.dumps(raw)).format == Format()


def test_version_4_state_starts_unsorted() -> None:
    raw = valid_raw()
    del raw["sort"]
    raw["v"] = 4
    assert from_json(json.dumps(raw)).sort == "none"


def test_round_trip_preserves_line_series_and_markers() -> None:
    fmt = Format(markers=False)
    state = make_state(kind="column", lines=(0, 2), secondary=(2,), format=fmt)
    restored = from_json(to_json(state))
    assert restored.lines == (0, 2)
    assert restored.secondary == (2,)
    assert restored.format == fmt


def test_round_trip_preserves_series_colours_and_the_scale_group() -> None:
    state = make_state(colors=(2, None, 0), scale_group="abc123")
    restored = from_json(to_json(state))
    assert restored.colors == (2, None, 0)
    assert restored.scale_group == "abc123"


def test_version_7_state_gets_no_colours_and_its_own_scale() -> None:
    raw = valid_raw()
    del raw["colors"]
    del raw["scale_group"]
    raw["v"] = 7
    restored = from_json(json.dumps(raw))
    assert restored.version == SCHEMA_VERSION
    assert restored.colors == ()
    assert restored.scale_group is None


def test_version_8_state_is_no_doughnut() -> None:
    raw = valid_raw()
    del raw["doughnut"]
    raw["v"] = 8
    restored = from_json(json.dumps(raw))
    assert restored.version == SCHEMA_VERSION
    assert restored.doughnut is False


def test_round_trip_preserves_the_doughnut_flag() -> None:
    state = make_state(kind="pie", doughnut=True)
    assert from_json(to_json(state)) == state


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("colors", "red"),
        ("colors", [True]),
        ("colors", ["blue"]),
        ("scale_group", 3),
    ],
)
def test_invalid_colour_or_group_fields_are_rejected(field: str, value: object) -> None:
    raw = valid_raw()
    raw[field] = value
    with pytest.raises(StateError):
        from_json(json.dumps(raw))


@pytest.mark.parametrize("kind", ["line", "area"])
def test_line_and_area_charts_round_trip(kind: str) -> None:
    state = make_state(kind=kind)
    assert from_json(to_json(state)).kind == kind


@pytest.mark.parametrize("percent", [False, True])
def test_an_area_chart_keeps_its_percent_variant(percent: bool) -> None:
    state = make_state(kind="area", percent=percent)
    assert from_json(to_json(state)).percent is percent


def test_version_6_state_gets_no_line_series_and_shows_markers() -> None:
    raw = valid_raw()
    del raw["lines"]
    del raw["secondary"]
    raw["format"] = {k: v for k, v in raw["format"].items() if k != "markers"}
    raw["v"] = 6
    restored = from_json(json.dumps(raw))
    assert restored.version == SCHEMA_VERSION
    assert restored.lines == ()
    assert restored.secondary == ()
    assert restored.format.markers is True


@pytest.mark.parametrize(("kind", "percent"), [("mekko", True), ("column", False), ("bar", False)])
def test_version_3_state_is_migrated_with_a_percent_mekko(kind: str, percent: bool) -> None:
    raw = {**valid_raw(), "kind": kind, "v": 3}
    del raw["percent"]
    restored = from_json(json.dumps(raw))
    assert restored.percent is percent
    assert restored.version == SCHEMA_VERSION


def test_version_1_state_gets_no_annotations() -> None:
    raw = valid_raw()
    del raw["annotations"]
    raw["v"] = 1
    restored = from_json(json.dumps(raw))
    assert restored.annotations == ()
    assert restored.version == SCHEMA_VERSION


def test_round_trip_keeps_unicode_and_formulas() -> None:
    state = make_state(cells=(("Größe", "=SUM(B2:C2)"),), values=((None, 3.5),))
    restored = from_json(to_json(state))
    assert restored.cells == (("Größe", "=SUM(B2:C2)"),)


def test_serialisation_is_compact_and_versioned() -> None:
    text = to_json(make_state())
    assert " " not in text.replace("Sales", "")
    assert json.loads(text)["v"] == SCHEMA_VERSION


def test_integers_in_values_become_floats() -> None:
    raw = valid_raw()
    raw["values"] = [[None, None, None], [None, 10, 20]]
    assert from_json(json.dumps(raw)).values[1] == (None, 10.0, 20.0)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("kind"),
        lambda r: r.pop("v"),
        lambda r: r.update(v="1"),
        lambda r: r.update(v=True),
        lambda r: r.update(v=0),
        lambda r: r.update(kind="spiral"),
        lambda r: r.update(doughnut=True),
        lambda r: r.update(doughnut="yes"),
        lambda r: r.pop("doughnut"),
        lambda r: r.update(grouping="diagonal"),
        lambda r: r.update(cells="abc"),
        lambda r: r.update(cells=[["a"], 5]),
        lambda r: r.update(cells=[[1, 2, 3], [4, 5, 6]]),
        lambda r: r.update(values=[[None, None, None], [None, "10", 20]]),
        lambda r: r.update(values=[[None, None, None], [None, True, 20]]),
        lambda r: r.update(values=[[None, None, None]]),
        lambda r: r.update(values=[[None, None], [None, 1]]),
        lambda r: r.pop("percent"),
        lambda r: r.update(percent="yes"),
        lambda r: r.update(percent=1),
        lambda r: r.update(kind="waterfall", percent=True),
        lambda r: r.update(kind="waterfall", sort="descending"),
        lambda r: r.update(sort="sideways"),
        lambda r: r.pop("sort"),
        lambda r: r.pop("format"),
        lambda r: r.update(format=[]),
        lambda r: r.update(format={**r["format"], "axis": "yes"}),
        lambda r: r.update(format={**r["format"], "gridlines": 1}),
        lambda r: r.update(format={**r["format"], "series_names": "pie"}),
        lambda r: r.update(format={**r["format"], "decimals": 5}),
        lambda r: r.update(format={**r["format"], "decimals": True}),
        lambda r: r.update(format={**r["format"], "magnitude": 4}),
        lambda r: r.update(format={**r["format"], "unit": 5}),
        lambda r: r.update(format={**r["format"], "separator": ";"}),
        lambda r: r.update(format={**r["format"], "language": "deu"}),
        lambda r: r.update(format={**r["format"], "markers": "yes"}),
        lambda r: r.pop("lines"),
        lambda r: r.update(lines="0"),
        lambda r: r.update(lines=[True]),
        lambda r: r.update(lines=[-1]),
        lambda r: r.update(lines=[0, 0]),
        lambda r: r.update(secondary=[0]),
        lambda r: r.update(lines=[0], percent=True),
        lambda r: r.pop("secondary"),
        lambda r: r.update(secondary="0"),
        lambda r: r.update(annotations=[{**ARROW, "value": "1"}]),
        lambda r: r.update(annotations=[{**BREAK, "value": 1.0}]),
        lambda r: r.update(annotations=[{**ARROW, "kind": "value_line", "value": True}]),
        lambda r: r.pop("annotations"),
        lambda r: r.update(annotations={}),
        lambda r: r.update(annotations=[5]),
        lambda r: r.update(annotations=[{**ARROW, "kind": "pie"}]),
        lambda r: r.update(annotations=[{**ARROW, "style": "curly"}]),
        lambda r: r.update(annotations=[{**ARROW, "label": "roman"}]),
        lambda r: r.update(annotations=[{**ARROW, "start": "0"}]),
        lambda r: r.update(annotations=[{**ARROW, "end": True}]),
        lambda r: r.update(annotations=[{**ARROW, "end": -1}]),
        lambda r: r.update(annotations=[{**ARROW, "series": 1.5}]),
        lambda r: r.update(annotations=[{**ARROW, "end": 0}]),
        lambda r: r.update(annotations=[{**ARROW, "lower": 1.0, "upper": 2.0}]),
        lambda r: r.update(annotations=[{**BREAK, "lower": 1.0}]),
        lambda r: r.update(annotations=[{**BREAK, "lower": 5.0, "upper": 2.0}]),
        lambda r: r.update(annotations=[{**BREAK, "lower": -1.0, "upper": 2.0}]),
        lambda r: r.update(annotations=[{**BREAK, "lower": "1", "upper": 2.0}]),
        lambda r: r.update(annotations=[{k: v for k, v in BREAK.items() if k != "upper"}]),
        lambda r: r.update(annotations=[{**ARROW, "kind": "axis_break"}]),
        lambda r: r.update(annotations=[{k: v for k, v in ARROW.items() if k != "label"}]),
    ],
)
def test_malformed_state_is_rejected(mutate: Any) -> None:
    raw = valid_raw()
    mutate(raw)
    with pytest.raises(StateError):
        from_json(json.dumps(raw))


@pytest.mark.parametrize("text", ["", "not json", "[]", "42", '{"v": 1, "values": NaN}'])
def test_garbage_is_rejected(text: str) -> None:
    with pytest.raises(StateError):
        from_json(text)


def test_non_finite_values_are_rejected_by_the_model() -> None:
    with pytest.raises(ValueError, match="finite"):
        make_state(values=((None, None, None), (None, float("inf"), 1.0)))


def test_state_from_newer_version_is_rejected() -> None:
    raw = valid_raw()
    raw["v"] = SCHEMA_VERSION + 1
    with pytest.raises(StateError, match="newer"):
        from_json(json.dumps(raw))


def test_older_state_is_migrated(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = valid_raw()
    raw["grouping"] = "legacy-name"

    def upgrade(old: dict[str, Any]) -> dict[str, Any]:
        return {**old, "grouping": "clustered"}

    newer = SCHEMA_VERSION + 1
    monkeypatch.setattr("librecharts.core.state_io.SCHEMA_VERSION", newer)
    monkeypatch.setattr("librecharts.core.model.SCHEMA_VERSION", newer)
    monkeypatch.setitem(state_io._MIGRATIONS, SCHEMA_VERSION, upgrade)  # pyright: ignore[reportPrivateUsage]

    restored = from_json(json.dumps(raw))
    assert restored.grouping == "clustered"
    assert restored.version == newer


@pytest.mark.parametrize("bounds", [(1.0, float("inf")), (float("nan"), 5.0)])
def test_the_model_rejects_a_non_finite_axis_break_range(bounds: tuple[float, float]) -> None:
    with pytest.raises(ValueError, match="finite"):
        Annotation("axis_break", 0, 0, lower=bounds[0], upper=bounds[1])
