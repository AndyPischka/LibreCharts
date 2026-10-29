from dataclasses import replace

import pytest

from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.format import (
    MAGNITUDE_SUFFIXES,
    changed,
    default_format,
    format_options,
    language_of,
    magnitude_suffix,
    number_format,
    separator_for_locale,
    settled,
    supports,
)
from librecharts.core.model import Format


@pytest.mark.parametrize(
    ("locale", "language"),
    [("de-DE", "de"), ("en-US", "en"), ("pt-BR", "pt"), ("", "en"), ("x", "en"), ("12-DE", "en")],
)
def test_language_of_a_locale(locale: str, language: str) -> None:
    assert language_of(locale) == language


def test_the_separator_follows_the_language() -> None:
    assert separator_for_locale("de-DE") == ","
    assert separator_for_locale("fr-FR") == ","
    assert separator_for_locale("en-US") == "."
    assert separator_for_locale("ja-JP") == "."


def test_magnitude_suffixes_are_localized() -> None:
    assert magnitude_suffix(3, "en") == "k"
    assert magnitude_suffix(6, "en") == "M"
    assert magnitude_suffix(9, "de") == "Mrd."
    assert magnitude_suffix(0, "de") == ""
    assert magnitude_suffix(6, "xx") == MAGNITUDE_SUFFIXES["en"][6]


@pytest.mark.parametrize(
    ("kind", "grouping", "names"),
    [
        ("column", "stacked", "labels"),
        ("column", "clustered", "legend"),
        ("bar", "stacked", "labels"),
        ("bar", "clustered", "legend"),
        ("mekko", "stacked", "labels"),
        ("waterfall", "stacked", "none"),
        ("line", "stacked", "labels"),
        ("area", "stacked", "labels"),
    ],
)
def test_new_charts_get_think_cell_series_names(kind: str, grouping: str, names: str) -> None:
    fmt = default_format(kind, grouping, "en-US")  # pyright: ignore[reportArgumentType]
    assert fmt.series_names == names
    assert not fmt.axis
    assert not fmt.gridlines
    assert fmt.separator == "."
    assert fmt.language == "en"


def test_a_german_locale_sets_comma_and_language() -> None:
    fmt = default_format("column", "stacked", "de-DE")
    assert fmt.separator == ","
    assert fmt.language == "de"


def test_which_chart_kinds_have_which_format_option() -> None:
    column = sample_state()
    waterfall = sample_waterfall_state()
    percent_mekko = sample_mekko_state()
    units_mekko = replace(sample_mekko_state(), percent=False)
    line = state_from_table("line", "stacked", [[None, "2024"], ["Sales", 10]])
    area = state_from_table("area", "stacked", [[None, "2024"], ["Sales", 10]])
    for option in ("axis", "gridlines", "series_names"):
        assert supports(column, option)
        assert supports(units_mekko, option)
        assert supports(line, option)
        assert supports(area, option)
    assert supports(waterfall, "axis")
    assert not supports(waterfall, "series_names")
    assert not supports(percent_mekko, "axis")
    assert supports(percent_mekko, "series_names")
    assert not supports(column, "decimals")


def test_markers_are_offered_for_lines_and_line_series_only() -> None:
    column = sample_state()
    line = state_from_table("line", "stacked", [[None, "2024"], ["Sales", 10]])
    area = state_from_table("area", "stacked", [[None, "2024"], ["Sales", 10]])
    assert supports(line, "markers")
    assert supports(replace(column, lines=(0,)), "markers")
    assert not supports(column, "markers")
    assert not supports(area, "markers")


def test_changed_applies_one_boolean_option() -> None:
    fmt = changed(Format(), "axis=true")
    assert fmt.axis
    assert not changed(fmt, "axis=false").axis
    assert changed(Format(), "gridlines=true").gridlines


def test_changed_applies_the_series_names() -> None:
    assert changed(Format(), "series_names=legend").series_names == "legend"
    assert changed(Format(), "series_names=none").series_names == "none"


def test_changed_switches_markers() -> None:
    assert changed(Format(), "markers=false").markers is False
    assert changed(Format(markers=False), "markers=true").markers is True


def test_the_format_rejects_a_non_boolean_markers_flag() -> None:
    with pytest.raises(ValueError, match="markers"):
        Format(markers="no")  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "axis=true&gridlines=true",
        "axis=yes",
        "series_names=pie",
        "decimals=2",
        "=true",
    ],
)
def test_changed_rejects_bad_queries(query: str) -> None:
    with pytest.raises(ValueError, match=r"option|argument|true or false|series_names"):
        changed(Format(), query)


def test_settled_checks_the_chart_kind() -> None:
    state = sample_state()
    assert settled(state, Format(), "axis=true").axis
    with pytest.raises(ValueError, match="no series_names"):
        settled(sample_waterfall_state(), Format(), "series_names=labels")
    with pytest.raises(ValueError, match="no axis"):
        settled(sample_mekko_state(), Format(), "axis=true")


def test_format_options_offer_the_axis_and_series_names() -> None:
    switches = format_options(sample_state())
    assert [(s.title, s.command) for s in switches] == [
        ("menu_axis_show", "ChangeFormat?axis=true"),
        ("menu_series_none", "ChangeFormat?series_names=none"),
        ("menu_series_labels", "ChangeFormat?series_names=labels"),
        ("menu_series_legend", "ChangeFormat?series_names=legend"),
    ]


def test_format_options_offer_the_marker_toggle_for_line_series() -> None:
    state = state_from_table("line", "stacked", [[None, "2024"], ["Sales", 10]])
    switches = format_options(state)
    assert [(s.title, s.command) for s in switches[-1:]] == [
        ("menu_markers_hide", "ChangeFormat?markers=false"),
    ]
    hidden = format_options(replace(state, format=Format(markers=False)))
    assert ("menu_markers_show", "ChangeFormat?markers=true") in [
        (s.title, s.command) for s in hidden
    ]


def test_gridlines_are_only_offered_with_an_axis() -> None:
    switches = format_options(replace(sample_state(), format=Format(axis=True)))
    assert [(s.title, s.command) for s in switches[:2]] == [
        ("menu_axis_hide", "ChangeFormat?axis=false"),
        ("menu_gridlines_show", "ChangeFormat?gridlines=true"),
    ]
    assert not any("gridlines" in s.title for s in format_options(sample_state()))


def test_number_format_parses_the_dialog_fields() -> None:
    fmt = number_format(Format(), "2", "6", "€", ",")
    assert isinstance(fmt, Format)
    assert (fmt.decimals, fmt.magnitude, fmt.unit, fmt.separator) == (2, 6, "€", ",")
    assert number_format(Format(decimals=1), "", "0", "", ".") == Format()
    assert number_format(Format(decimals=1), "Auto", "0", "", ".") == Format()
    assert number_format(Format(), "automatisch", "0", "", ".").decimals is None  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("decimals", "magnitude", "unit", "separator", "error"),
    [
        ("x", "0", "", ".", "format_decimals_invalid"),
        ("5", "0", "", ".", "format_decimals_invalid"),
        ("-1", "0", "", ".", "format_decimals_invalid"),
        ("2", "4", "", ".", "format_magnitude_invalid"),
        ("2", "0", "x" * 11, ".", "format_unit_too_long"),
        ("2", "0", "", ";", "format_separator_invalid"),
    ],
)
def test_number_format_rejects_bad_fields(
    decimals: str, magnitude: str, unit: str, separator: str, error: str
) -> None:
    assert number_format(Format(), decimals, magnitude, unit, separator) == error


def test_the_unit_may_be_ten_characters() -> None:
    fmt = number_format(Format(), "0", "0", "x" * 10, ".")
    assert isinstance(fmt, Format)
