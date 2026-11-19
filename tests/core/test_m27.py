"""M27: chart templates and deck specifications that use them."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import templates
from librecharts.core.datasheet import sample_state
from librecharts.core.deck import DeckError, chart_state
from librecharts.core.model import Link


def test_a_template_round_trips_and_strips_the_document_fields() -> None:
    state = replace(
        sample_state(),
        link=Link("file:///x.ods", "Sheet1", "A1:B2"),
        scale_group="group-1",
    )
    template = templates.Template("Stacked revenue", templates.stripped(state), "three years")
    restored = templates.from_json(templates.to_json(template))
    assert restored.name == "Stacked revenue"
    assert restored.description == "three years"
    assert restored.state.link is None
    assert restored.state.scale_group is None
    assert restored.state.kind == state.kind


def test_a_template_validates_name_and_description() -> None:
    with pytest.raises(ValueError, match="name"):
        templates.Template("", sample_state())
    with pytest.raises(ValueError, match="description"):
        templates.Template("x", sample_state(), "d" * 201)


def test_file_names_are_safe() -> None:
    assert templates.file_name("Revenue 2025/Q1") == "Revenue-2025-Q1.json"
    assert templates.file_name('<>:"/\\|?*') == "chart.json"
    assert templates.file_name(".") == "chart.json"


def test_a_newer_or_malformed_template_is_refused() -> None:
    with pytest.raises(templates.TemplateError, match="version"):
        templates.from_json('{"version": 99, "name": "x", "state": {}}')
    with pytest.raises(templates.TemplateError, match="JSON"):
        templates.from_json("{nope")
    with pytest.raises(templates.TemplateError, match="name"):
        templates.from_json('{"version": 1, "name": 3, "state": {}}')
    with pytest.raises(templates.TemplateError):
        templates.from_json('{"version": 1, "name": "x", "state": {"v": 99, "kind": "column"}}')


def test_the_deck_uses_a_template_and_lets_the_entry_win() -> None:
    base = templates.stripped(sample_state())
    resolved = chart_state(
        {"template": "revenue", "data": [[None, "A"], ["S", 3]]}, loader=lambda name: base
    )
    assert resolved.kind == base.kind
    assert resolved.cells == (("", "A"), ("S", "3"))
    without_data = chart_state({"template": "revenue"}, loader=lambda name: base)
    assert without_data.cells == base.cells
    overridden = chart_state({"template": "revenue", "kind": "bar"}, loader=lambda name: base)
    assert overridden.kind == "bar"


def test_an_unknown_template_names_the_reason() -> None:
    with pytest.raises(DeckError, match="deck_template_missing"):
        chart_state({"template": "missing"}, loader=lambda name: (_ for _ in ()).throw(OSError()))
    with pytest.raises(DeckError, match="deck_template_missing"):
        chart_state({"template": "missing"})
