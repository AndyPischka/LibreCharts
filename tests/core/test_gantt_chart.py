"""How the Gantt chart plugs into the shared modules (M10)."""

import json
from dataclasses import replace
from datetime import date

import pytest

from librecharts.core import samescale
from librecharts.core.datasheet import sample_gantt_state, sample_state
from librecharts.core.format import default_format, format_options, supports
from librecharts.core.gantt import serial
from librecharts.core.menu import PROTOCOL, MenuItem, chart_menu
from librecharts.core.model import Annotation, ChartState, Format
from librecharts.core.options import changed, sort_options, sort_toggle, variants
from librecharts.core.panel import content
from librecharts.core.picking import supports as can_annotate
from librecharts.core.state_io import from_json, to_json
from librecharts.core.value_line import check_date, date_input

JUNE_30 = float(serial(date(2026, 6, 30)))


def with_date_line(state: ChartState, value: float | None = JUNE_30) -> ChartState:
    return replace(state, annotations=(Annotation("value_line", 0, 0, value=value),))


def submenu(state: ChartState, title: str, locale: str = "en-US") -> MenuItem:
    return next(item for item in chart_menu(state, locale).children if item.title == title)


def commands(item: MenuItem) -> list[str]:
    return [child.command for child in item.children]


# --- model and state ---------------------------------------------------------------------------


def test_a_gantt_chart_sorts_by_ascending_start_date_only() -> None:
    assert replace(sample_gantt_state(), sort="ascending").sort == "ascending"
    with pytest.raises(ValueError, match="ascending start date"):
        replace(sample_gantt_state(), sort="descending")


def test_a_gantt_chart_round_trips() -> None:
    state = with_date_line(replace(sample_gantt_state(), sort="ascending"))
    assert from_json(to_json(state)) == state


def test_version_9_state_is_read_unchanged() -> None:
    raw = json.loads(to_json(sample_state()))
    raw["v"] = 9
    restored = from_json(json.dumps(raw))
    assert replace(restored, version=9) == replace(sample_state(), version=9)


# --- options and format ------------------------------------------------------------------------


def test_a_gantt_chart_has_no_variants_but_a_start_date_sort() -> None:
    state = sample_gantt_state()
    assert variants(state) == ()
    assert [(s.title, s.current) for s in sort_options(state)] == [
        ("menu_sort_none", True),
        ("menu_sort_start", False),
    ]
    toggle = sort_toggle(state)
    assert toggle is not None
    assert toggle.command == "ChangeChart?sort=ascending"
    sorted_state = changed(state, "sort=ascending")
    assert sorted_state.sort == "ascending"
    back = sort_toggle(sorted_state)
    assert back is not None
    assert back.command == "ChangeChart?sort=none"
    with pytest.raises(ValueError, match="ascending start date"):
        changed(state, "sort=descending")


def test_a_gantt_chart_has_gridlines_but_no_axis_series_names_or_number_format() -> None:
    state = sample_gantt_state()
    assert supports(state, "gridlines")
    for option in ("axis", "series_names", "markers", "number_format"):
        assert not supports(state, option), option
    assert supports(sample_state(), "number_format")
    assert [s.command for s in format_options(state)] == ["ChangeFormat?gridlines=true"]


def test_a_new_gantt_chart_starts_in_the_ui_language_without_gridlines() -> None:
    assert default_format("gantt", "stacked", "de-DE") == Format(separator=",", language="de")


def test_a_gantt_chart_has_no_scale_to_share() -> None:
    assert samescale.orientation(sample_gantt_state()) is None


def test_date_lines_are_the_only_annotation() -> None:
    state = sample_gantt_state()
    assert can_annotate(state, "value_line")
    for kind in ("difference", "cagr", "axis_break"):
        assert not can_annotate(state, kind), kind  # pyright: ignore[reportArgumentType]


# --- menu --------------------------------------------------------------------------------------


def test_the_menu_offers_date_lines_and_a_today_line() -> None:
    items = chart_menu(sample_gantt_state(), "en-US").children
    by_title = {item.title: item.command for item in items}
    assert by_title["Add date line..."] == PROTOCOL + "ValueLine"
    assert by_title["Add today line"] == PROTOCOL + "TodayLine"
    assert "Add value line..." not in by_title
    assert "Add value line..." in [item.title for item in chart_menu(sample_state(), "en").children]


def test_the_menu_sorts_by_start_date_and_formats_without_number_format() -> None:
    state = sample_gantt_state()
    assert commands(submenu(state, "Sort categories")) == [PROTOCOL + "ChangeChart?sort=ascending"]
    assert [c.title for c in submenu(state, "Format").children] == ["Show gridlines"]


def test_series_colours_are_per_phase() -> None:
    names = [item.title for item in submenu(sample_gantt_state(), "Series colour").children]
    assert names == ["Concept", "Implementation"]
    unphased = replace(
        sample_gantt_state(),
        cells=tuple(row[:4] for row in sample_gantt_state().cells),
        values=tuple(row[:4] for row in sample_gantt_state().values),
    )
    assert [item.title for item in submenu(unphased, "Reihenfarbe", "de-DE").children] == ["Balken"]


def test_a_date_line_is_listed_with_its_date_in_the_chart_language() -> None:
    state = replace(with_date_line(sample_gantt_state()), format=Format(language="de"))
    (entry,) = [
        i for i in chart_menu(state, "de-DE").children if i.title.startswith("Datumslinie (")
    ]
    assert entry.title == "Datumslinie (30.06.2026)"
    assert [c.title for c in entry.children] == ["Datumslinie ändern...", "Entfernen"]
    assert commands(entry)[0] == PROTOCOL + "EditValueLine?index=0"
    average = with_date_line(sample_gantt_state(), None)
    assert "Date line (average)" in [i.title for i in chart_menu(average, "en").children]


# --- panel -------------------------------------------------------------------------------------


def test_the_panel_counts_rows_and_offers_a_today_line() -> None:
    panel = content(with_date_line(sample_gantt_state()), True, "en-US")
    assert panel.status == "Gantt chart, 9 rows"
    assert [(b.title, b.command) for b in panel.add[-2:]] == [
        ("Add date line...", PROTOCOL + "ValueLine"),
        ("Add today line", PROTOCOL + "TodayLine"),
    ]
    assert all(b.enabled for b in panel.add[-2:])
    assert [row.title for row in panel.rows] == ["Date line (30 Jun 2026)"]
    assert "Number format..." not in [b.title for b in panel.format]
    assert [b.title for b in panel.options] == ["By start date"]
    assert content(sample_gantt_state(), True, "de-DE").status == "Gantt-Diagramm, 9 Zeilen"


def test_other_charts_get_no_today_line_button() -> None:
    commands = [b.command for b in content(sample_state(), True, "en-US").add]
    assert PROTOCOL + "TodayLine" not in commands


# --- date input --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("2026-06-30", "en"),
        ("2026-06-30", "de"),
        ("30.06.2026", "de"),
        ("30.6.26", "en"),
        (" 6/30/2026 ", "en"),
        ("30/6/2026", "de"),
    ],
)
def test_dates_are_entered_in_the_charts_language(text: str, language: str) -> None:
    assert check_date(text, language) == JUNE_30


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("", "en"),
        ("tomorrow", "en"),
        ("30.06.", "de"),
        ("31.06.2026", "de"),
        ("30/6/2026", "en"),
        ("26-06-30", "en"),
        ("2026-06", "en"),
        ("1.1.0999", "de"),
    ],
)
def test_invalid_dates_are_rejected(text: str, language: str) -> None:
    assert check_date(text, language) == "date_line_invalid"


def test_the_dialog_shows_a_date_line_per_language() -> None:
    assert date_input(JUNE_30, "de") == "30.06.2026"
    assert date_input(JUNE_30, "en") == "2026-06-30"
    assert date_input(1e9, "en") == ""
