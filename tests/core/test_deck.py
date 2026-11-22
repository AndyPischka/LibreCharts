"""The deck specification (M18, ADR 0028): parsing, defaults and validation messages."""

from __future__ import annotations

import json
from datetime import date

import pytest

from librecharts.core import deck
from librecharts.core.deck import DeckError

DATA = [[None, "2023", "2024"], ["Product A", 10, 12], ["Product B", 20, 22]]


def spec(**chart: object) -> dict[str, object]:
    """A deck specification with one chart; ``chart`` overrides its fields."""
    entry = {"placeholder": "revenue", "kind": "column", "data": DATA, **chart}
    return {"version": 1, "charts": [entry]}


def text(raw: object) -> str:
    return json.dumps(raw)


def key_of(raw: object, locale: str = "en") -> str:
    with pytest.raises(DeckError) as error:
        deck.parse(text(raw), locale)
    return error.value.key


def test_a_chart_carries_its_placeholder_and_data() -> None:
    (chart,) = deck.parse(text(spec())).charts
    assert chart.placeholder == "revenue"
    assert chart.state.kind == "column"
    assert chart.state.grouping == "stacked"
    assert chart.state.cells[0] == ("", "2023", "2024")
    assert chart.state.values[1] == (None, 10.0, 12.0)


def test_text_cells_and_gaps_stay() -> None:
    (chart,) = deck.parse(text(spec(data=[[None, "A", "B"], ["x", 1, None]]))).charts
    assert chart.state.cells[1] == ("x", "1", "")
    assert chart.state.values[1] == (None, 1.0, None)


def test_charts_keep_their_file_order() -> None:
    raw = {
        "charts": [
            {"placeholder": "b", "kind": "pie", "data": DATA},
            {"placeholder": "a", "kind": "bar", "data": DATA},
        ]
    }
    assert [chart.placeholder for chart in deck.parse(text(raw)).charts] == ["b", "a"]


def test_the_locale_fills_the_format_defaults() -> None:
    german = deck.parse(text(spec()), "de-DE").charts[0].state.format
    assert (german.separator, german.language) == (",", "de")
    english = deck.parse(text(spec()), "en-US").charts[0].state.format
    assert (english.separator, english.language) == (".", "en")


def test_a_new_chart_gets_the_series_names_of_its_kind() -> None:
    assert deck.parse(text(spec())).charts[0].state.format.series_names == "labels"
    clustered = deck.parse(text(spec(grouping="clustered"))).charts[0].state.format
    assert clustered.series_names == "legend"


def test_the_format_of_the_specification_wins() -> None:
    raw = spec(
        format={
            "axis": True,
            "gridlines": True,
            "decimals": 0,
            "magnitude": 3,
            "unit": "k",
            "series_names": "legend",
        }
    )
    fmt = deck.parse(text(raw), "de-DE").charts[0].state.format
    assert (fmt.axis, fmt.gridlines, fmt.decimals) == (True, True, 0)
    assert (fmt.magnitude, fmt.unit, fmt.series_names) == (3, "k", "legend")
    assert (fmt.separator, fmt.language) == (",", "de")  # untouched defaults survive


def test_the_options_of_a_chart_are_applied() -> None:
    raw = spec(percent=True, sort="descending", colors=[2, None])
    state = deck.parse(text(raw)).charts[0].state
    assert (state.percent, state.sort) == (True, "descending")
    assert state.colors == (2, None)


def test_a_mekko_chart_can_be_a_percent_chart() -> None:
    state = deck.parse(text(spec(kind="mekko", percent=True))).charts[0].state
    assert (state.kind, state.percent) == ("mekko", True)


def test_line_series_and_secondary_axis() -> None:
    raw = spec(lines=[2, 3], secondary=[3])
    state = deck.parse(text(raw)).charts[0].state
    assert (state.lines, state.secondary) == ((2, 3), (3,))


def test_a_line_chart_can_interpolate_missing_values() -> None:
    state = deck.parse(text(spec(kind="line", interpolate=True))).charts[0].state
    assert state.interpolate is True
    assert deck.parse(text(spec(kind="line"))).charts[0].state.interpolate is False


def test_interpolation_is_rejected_for_other_charts_and_bad_values() -> None:
    assert key_of(spec(interpolate=True)) == "deck_invalid_chart"  # a column chart
    assert key_of(spec(kind="line", interpolate="yes")) == "deck_invalid_chart"


def test_a_gantt_calendar_is_read() -> None:
    raw = spec(kind="gantt", calendar={"working_days": [0, 1, 2], "holidays": ["2026-12-25"]})
    state = deck.parse(text(raw)).charts[0].state
    assert state.calendar.working_days == (0, 1, 2)
    assert state.calendar.holidays == (date(2026, 12, 25),)


def test_a_gantt_calendar_defaults_to_every_day() -> None:
    state = deck.parse(text(spec(kind="gantt"))).charts[0].state
    assert state.calendar.working_days == (0, 1, 2, 3, 4, 5, 6)
    assert state.calendar.holidays == ()


def test_a_chart_of_one_object_needs_no_placeholder() -> None:
    chart = deck.parse_chart(text({"kind": "pie", "data": DATA}))
    assert chart.placeholder == ""
    assert chart.state.kind == "pie"


def test_a_chart_of_one_object_keeps_a_placeholder() -> None:
    chart = deck.parse_chart(text({"placeholder": "x", "kind": "pie", "data": DATA}))
    assert chart.placeholder == "x"


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("[]", "deck_bad_spec"),
        ("7", "deck_bad_spec"),
        ({"version": 2, "charts": spec()["charts"]}, "deck_bad_version"),
        ({"charts": []}, "deck_no_charts"),
        ({"charts": {"x": 1}}, "deck_no_charts"),
        ({"charts": [1]}, "deck_bad_chart"),
        ({"charts": ["x"]}, "deck_bad_chart"),
        ({"charts": spec()["charts"], "extra": 1}, "deck_unknown_key"),
        (spec(extra=1), "deck_unknown_key"),
        (spec(placeholder=None), "deck_no_placeholder"),
        (spec(placeholder="  "), "deck_no_placeholder"),
        (spec(kind="donut"), "deck_bad_kind"),
        (spec(kind=None), "deck_bad_kind"),
        (spec(data=[]), "deck_bad_data"),
        (spec(data=[[None, "A"]]), "deck_bad_data"),
        (spec(data=[[None], ["A", 1]]), "deck_bad_data"),
        (spec(data=[[None, "A"], ["x", 1, 2]]), "deck_bad_data"),
        (spec(data=[[None, "A"], ["x", True]]), "deck_bad_data"),
        (spec(data=[[None, "A"], ["x", {"y": 1}]]), "deck_bad_data"),
        (spec(percent="yes"), "deck_invalid_chart"),
        (spec(sort=3), "deck_invalid_chart"),
        (spec(lines=[-1]), "deck_invalid_chart"),
        (spec(colors="red"), "deck_invalid_chart"),
        (spec(kind="line", percent=True), "deck_invalid_chart"),
        (spec(format="axis"), "deck_invalid_chart"),
        (spec(format={"axis": "yes"}), "deck_invalid_chart"),
        (spec(format={"nonsense": 1}), "deck_invalid_chart"),
        (spec(kind="gantt", calendar={"working_days": []}), "deck_bad_calendar"),
        (spec(kind="gantt", calendar={"holidays": ["25.12.2026"]}), "deck_bad_calendar"),
        (spec(kind="gantt", calendar={"working_days": [7]}), "deck_bad_calendar"),
        (spec(kind="gantt", calendar={"weekend": True}), "deck_unknown_key"),
        (spec(kind="gantt", calendar=[]), "deck_bad_calendar"),
    ],
)
def test_bad_input_names_its_reason(raw: object, key: str) -> None:
    assert key_of(raw) == key


def test_broken_json_is_rejected() -> None:
    for raw in ("{", "", "not json", '{"charts": [}'):
        with pytest.raises(DeckError) as error:
            deck.parse(raw)
        assert error.value.key == "deck_bad_json"


def test_nan_is_no_data_sheet_value() -> None:
    raw = text(spec()).replace("10", "NaN")
    with pytest.raises(DeckError) as error:
        deck.parse(raw)
    assert error.value.key == "deck_bad_json"


def test_a_duplicate_placeholder_is_rejected() -> None:
    raw = {"charts": [spec()["charts"][0], spec()["charts"][0]]}  # type: ignore[index]
    assert key_of(raw) == "deck_duplicate_placeholder"


def test_a_too_large_grid_is_rejected() -> None:
    columns = deck.MAX_CELLS // 2 + 1
    raw = spec(data=[[None] * columns, ["x"] * columns])
    assert key_of(raw) == "deck_too_large"


def test_a_problem_names_the_placeholder_and_speaks_both_languages() -> None:
    raw = spec(percent="yes")
    for locale, expected in (("en", "placeholder revenue"), ("de", "Platzhalter revenue")):
        with pytest.raises(DeckError) as error:
            deck.parse(text(raw), locale)
        assert expected in error.value.message(locale)


def test_an_invalid_placeholder_of_one_chart_is_ignored_by_chart_parsing() -> None:
    with pytest.raises(DeckError) as error:
        deck.parse_chart(text({"placeholder": 3, "kind": "pie", "data": DATA}))
    assert error.value.key == "deck_no_placeholder"


def test_a_broken_chart_object_is_rejected() -> None:
    for raw in ("{", "[]"):
        with pytest.raises(DeckError) as error:
            deck.parse_chart(raw)
        assert error.value.key in ("deck_bad_json", "deck_bad_chart")


def test_placeholders_are_named_and_read_back() -> None:
    name = deck.placeholder_name("revenue")
    assert name == "librecharts-placeholder:revenue"
    assert deck.placeholder_key(name) == "revenue"
    assert deck.placeholder_key("librecharts-placeholder: revenue ") == "revenue"


@pytest.mark.parametrize(
    "name", ["librecharts-placeholder:", "librecharts-placeholder:  ", "Rectangle 1", ""]
)
def test_names_that_are_no_placeholder(name: str) -> None:
    assert deck.placeholder_key(name) is None


def test_the_reports_speak_both_languages() -> None:
    assert deck.unused_report([], "en") == ""
    assert "revenue" in deck.unused_report(["revenue", "costs"], "en")
    assert "leer" in deck.unused_report(["revenue"], "de")
    assert deck.built_report(2, "deck.odp", "en") == "2 charts written to deck.odp."
    assert deck.built_report(2, "deck.odp", "de") == "2 Diagramme in deck.odp geschrieben."
