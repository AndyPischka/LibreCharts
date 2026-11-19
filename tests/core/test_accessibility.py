"""M20: alternative text, patterns beside colours, CSV export."""

import csv
import io
from dataclasses import replace

import pytest

from librecharts.core import alttext, csvexport, style
from librecharts.core.datasheet import (
    sample_gantt_state,
    sample_mekko_state,
    sample_pie_state,
    sample_scatter_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.format import changed, format_options, supports
from librecharts.core.model import Format
from librecharts.core.state_io import from_json, to_json


def test_a_column_chart_describes_every_series_in_its_language() -> None:
    state = sample_state()
    assert alttext.title(state) == "Column chart"
    assert alttext.description(state) == (
        "Column chart with 3 categories and 3 series. "
        "Product A: 2023 = 10, 2024 = 12, 2025 = 15. "
        "Product B: 2023 = 20, 2024 = 22, 2025 = 21. "
        "Product C: 2023 = 5, 2024 = 8, 2025 = 9."
    )
    german = replace(state, format=Format(language="de", separator=","))
    assert alttext.description(german).startswith(
        "Säulendiagramm mit 3 Kategorien und 3 Datenreihen."
    )


def test_numbers_follow_the_chart_format_and_gaps_are_named() -> None:
    state = state_from_table("bar", "stacked", [[None, "A", "B"], ["Sales", 1500.5, None]])
    state = replace(state, format=Format(magnitude=3, unit="EUR", separator=",", language="de"))
    assert alttext.description(state).endswith("Sales: A = 1,5 Tsd. EUR, B = kein Wert.")


@pytest.mark.parametrize(
    ("state", "key"),
    [
        (replace(sample_state(), percent=True), "column_percent"),
        (replace(sample_mekko_state(), percent=False), "mekko_units"),
        (replace(sample_pie_state(), doughnut=True), "doughnut"),
        (sample_scatter_state(), "scatter"),
        (sample_gantt_state(), "gantt"),
    ],
)
def test_the_kind_key_names_the_variant(state: object, key: str) -> None:
    assert alttext.kind_key(state) == key  # type: ignore[arg-type]


def test_a_waterfall_lists_its_steps_with_signs_and_totals() -> None:
    text = alttext.description(sample_waterfall_state())
    assert text.startswith("Waterfall chart with ")
    assert "+" in text
    assert "-" in text
    assert " = " in text


def test_a_scatter_chart_lists_its_points() -> None:
    text = alttext.description(sample_scatter_state())
    assert text.startswith("Scatter chart with ")
    assert "x = " in text
    assert "y = " in text


def test_a_bubble_chart_names_the_sizes() -> None:
    state = state_from_table("scatter", "stacked", [["", "x", "y", "size"], ["P", 1, 2, 3]])
    assert alttext.description(state) == "Bubble chart with 1 points. P: x = 1, y = 2, size 3."


def test_a_gantt_chart_lists_its_rows_with_dates() -> None:
    text = alttext.description(sample_gantt_state())
    assert text.startswith("Gantt chart with ")
    assert " to " in text


def test_a_chart_without_data_says_so() -> None:
    empty = state_from_table("column", "stacked", [[None, None], [None, None]])
    assert alttext.description(empty) == "Column chart without data."
    for kind in ("waterfall", "scatter"):
        assert alttext.description(replace(empty, kind=kind)).endswith("without data.")  # type: ignore[arg-type]
    gantt = sample_gantt_state()
    assert alttext.description(replace(gantt, cells=gantt.cells[:1], values=gantt.values[:1])) == (
        "Gantt chart without data."
    )


def test_a_long_description_is_cut() -> None:
    row = [None, *(f"Category {index}" for index in range(400))]
    state = state_from_table("column", "stacked", [row, ["S", *range(400)]])
    text = alttext.description(state)
    assert len(text) <= alttext.MAX_DESCRIPTION
    assert text.endswith(alttext.ELLIPSIS)


def test_patterns_differ_for_neighbouring_series_and_the_first_stays_plain() -> None:
    assert style.hatch(0) is None
    assert style.dash(0) is None
    hatches = [style.hatch(series) for series in range(len(style.HATCHES))]
    assert len(set(hatches)) == len(hatches)
    assert style.hatch(len(style.HATCHES)) is None
    assert style.hatch(-1) is None
    assert style.dash(-2) is None
    assert style.dash(1) is not None


def test_a_hatch_is_drawn_half_way_to_the_text_colour() -> None:
    assert style.hatch_color(0xFFFFFF) == style.mix(0xFFFFFF, 0x000000, 0.55)
    assert style.hatch_color(0x000000) == style.mix(0x000000, 0xFFFFFF, 0.55)


def test_patterns_are_a_format_switch_of_every_chart() -> None:
    state = sample_state()
    assert supports(state, "patterns")
    assert format_options(state)[-1].command == "ChangeFormat?patterns=true"
    shown = replace(state, format=changed(state.format, "patterns=true"))
    assert shown.format.patterns
    assert format_options(shown)[-1].title == "menu_patterns_hide"
    with pytest.raises(ValueError, match="patterns must be true or false"):
        Format(patterns="yes")  # type: ignore[arg-type]


def test_patterns_survive_saving_and_old_states_load_without_them() -> None:
    state = replace(sample_state(), format=Format(patterns=True))
    assert from_json(to_json(state)).format.patterns
    old = to_json(sample_state()).replace('"v":16', '"v":15').replace(',"patterns":false', "")
    assert not from_json(old).format.patterns


def read(content: str, delimiter: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(content), delimiter=delimiter))


def test_csv_holds_the_data_sheet_with_a_decimal_point_and_commas() -> None:
    state = state_from_table("column", "stacked", [[None, "2024", "2025"], ["A, Inc.", 1.5, 2]])
    content = csvexport.to_csv(state)
    assert content.endswith("\r\n")
    assert read(content, ",") == [["", "2024", "2025"], ["A, Inc.", "1.5", "2"]]


def test_csv_with_a_decimal_comma_uses_semicolons() -> None:
    state = state_from_table("column", "stacked", [[None, "X"], ["A", 1.25]])
    state = replace(state, format=Format(separator=","))
    assert csvexport.delimiter(state) == ";"
    assert read(csvexport.to_csv(state), ";") == [["", "X"], ["A", "1,25"]]


def test_csv_exports_gantt_dates_as_iso_dates() -> None:
    rows = csvexport.rows(sample_gantt_state())
    first = rows[1]
    assert first[1][:2] == "20"
    assert first[1][4] == "-"


def test_csv_drops_trailing_empty_rows_and_columns() -> None:
    state = state_from_table(
        "column", "stacked", [[None, "X", None], ["A", 1, None], [None, None, None]]
    )
    assert csvexport.rows(state) == [["", "X"], ["A", "1"]]


@pytest.mark.parametrize(
    ("value", "separator", "expected"),
    [
        (12.0, ".", "12"),
        (0.125, ".", "0.125"),
        (-3.5, ",", "-3,5"),
        (1e-7, ".", "0.0000001"),
        (1e20, ".", "100000000000000000000"),
    ],
)
def test_numbers_are_written_without_loss_or_exponent(
    value: float, separator: str, expected: str
) -> None:
    assert csvexport.number(value, separator) == expected
