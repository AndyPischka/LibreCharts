import json
from typing import Any

import pytest

from librecharts.core import state_io
from librecharts.core.model import SCHEMA_VERSION, ChartState
from librecharts.core.state_io import StateError, from_json, to_json


def make_state(**overrides: Any) -> ChartState:
    fields: dict[str, Any] = {
        "kind": "column",
        "grouping": "stacked",
        "cells": (("", "2024", "2025"), ("Sales", "10", "=B2*2")),
        "values": ((None, None, None), (None, 10.0, 20.0)),
    }
    return ChartState(**{**fields, **overrides})


def valid_raw() -> dict[str, Any]:
    return json.loads(to_json(make_state()))


def test_round_trip_preserves_state() -> None:
    state = make_state(grouping="clustered")
    assert from_json(to_json(state)) == state


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
        lambda r: r.update(kind="pie"),
        lambda r: r.update(grouping="diagonal"),
        lambda r: r.update(cells="abc"),
        lambda r: r.update(cells=[["a"], 5]),
        lambda r: r.update(cells=[[1, 2, 3], [4, 5, 6]]),
        lambda r: r.update(values=[[None, None, None], [None, "10", 20]]),
        lambda r: r.update(values=[[None, None, None], [None, True, 20]]),
        lambda r: r.update(values=[[None, None, None]]),
        lambda r: r.update(values=[[None, None], [None, 1]]),
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

    def v1_to_v2(old: dict[str, Any]) -> dict[str, Any]:
        return {**old, "grouping": "clustered"}

    monkeypatch.setattr("librecharts.core.state_io.SCHEMA_VERSION", 2)
    monkeypatch.setattr("librecharts.core.model.SCHEMA_VERSION", 2)
    monkeypatch.setitem(state_io._MIGRATIONS, 1, v1_to_v2)  # pyright: ignore[reportPrivateUsage]

    restored = from_json(json.dumps(raw))
    assert restored.grouping == "clustered"
    assert restored.version == 2
