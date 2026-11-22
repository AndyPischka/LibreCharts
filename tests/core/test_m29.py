"""M29: audit reports and exporting a deck specification."""

from __future__ import annotations

import json

from librecharts.core import audit, deck_export
from librecharts.core.datasheet import sample_state


def test_an_audit_report_lists_findings_by_slide() -> None:
    report = audit.report((audit.Finding(2, "audit_linked"),), "en")
    assert "1 findings" in report
    assert "Slide 2" in report
    assert "linked" in report


def test_an_empty_audit_is_clean() -> None:
    assert audit.report((), "en") == "No problems found."


def test_a_deck_specification_round_trips_through_the_parser() -> None:
    from librecharts.core.deck import parse

    state = sample_state()
    text = deck_export.to_json([("revenue", state)])
    parsed = json.loads(text)
    assert parsed["version"] == 1
    assert parsed["charts"][0]["placeholder"] == "revenue"
    assert parse(text).charts[0].state.cells == state.cells


def test_interpolation_is_exported_and_read_back() -> None:
    from dataclasses import replace

    from librecharts.core.datasheet import sample_line_state
    from librecharts.core.deck import parse

    state = replace(sample_line_state(), interpolate=True)
    text = deck_export.to_json([("trend", state)])
    assert json.loads(text)["charts"][0]["interpolate"] is True
    assert parse(text).charts[0].state.interpolate is True
