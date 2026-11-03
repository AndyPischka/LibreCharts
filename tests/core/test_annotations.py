from dataclasses import replace

import pytest

from librecharts.core.annotations import (
    NOT_AVAILABLE,
    added,
    category_gaps,
    changed,
    check_bracket_text,
    drawable,
    from_query,
    group_brackets,
    label,
    measured,
    measured_value,
    removed,
)
from librecharts.core.datasheet import (
    ChartData,
    Series,
    sample_mekko_state,
    sample_pie_state,
    sample_scatter_state,
)
from librecharts.core.model import Annotation

YEARS = ChartData(
    ("2020", "2021", "2025"),
    (Series("A", (10.0, 12.0, 20.0)), Series("B", (10.0, None, 0.0))),
)


def test_measured_value_is_the_column_total_or_one_series() -> None:
    assert measured_value(YEARS, 0, None) == 20.0
    assert measured_value(YEARS, 1, None) == 12.0  # gaps are skipped
    assert measured_value(YEARS, 2, 1) == 0.0
    assert measured_value(YEARS, 1, 1) is None


def test_measured_value_of_an_empty_column_is_none() -> None:
    chart = ChartData(("X",), (Series("A", (None,)),))
    assert measured_value(chart, 0, None) is None


@pytest.mark.parametrize(
    ("annotation", "text"),
    [
        (Annotation("difference", 0, 2), "0%"),  # 20 -> 20
        (Annotation("difference", 0, 1), "-40%"),  # 20 -> 12
        (Annotation("difference", 1, 0), "+66.7%"),  # 12 -> 20
        (Annotation("difference", 0, 1, label="absolute"), "-8"),
        (Annotation("difference", 0, 2, series=0, label="absolute"), "+10"),
        (Annotation("difference", 0, 2, series=1), "-100%"),
        (Annotation("difference", 2, 0, series=1), NOT_AVAILABLE),  # from zero
        (Annotation("difference", 0, 1, series=1), NOT_AVAILABLE),  # gap
    ],
)
def test_difference_labels(annotation: Annotation, text: str) -> None:
    assert label(annotation, YEARS) == text


def test_cagr_counts_years_from_the_category_names() -> None:
    # 10 -> 20 over 2020..2025: 5 years, 2 ** (1/5) - 1 = 14.87 %
    assert label(Annotation("cagr", 0, 2, series=0), YEARS) == "CAGR +14.9%"
    assert label(Annotation("cagr", 2, 0, series=0), YEARS) == "CAGR +14.9%"  # either direction


def test_cagr_counts_columns_without_year_names() -> None:
    chart = ChartData(("Q1", "Q2", "Q3"), (Series("A", (100.0, None, 121.0)),))
    assert label(Annotation("cagr", 0, 2), chart) == "CAGR +10%"


def test_cagr_falls_back_to_columns_for_unordered_years() -> None:
    chart = ChartData(("2025", "2020"), (Series("A", (100.0, 110.0)),))
    assert label(Annotation("cagr", 0, 1), chart) == "CAGR +10%"


@pytest.mark.parametrize("values", [(0.0, 10.0), (-5.0, 10.0), (10.0, -5.0)])
def test_cagr_needs_positive_start_and_non_negative_end(values: tuple[float, float]) -> None:
    chart = ChartData(("2020", "2021"), (Series("A", values),))
    assert label(Annotation("cagr", 0, 1), chart) == "CAGR " + NOT_AVAILABLE


def test_tiny_differences_show_as_zero_without_sign() -> None:
    chart = ChartData(("A", "B"), (Series("S", (1000.0, 1000.1)),))
    assert label(Annotation("difference", 0, 1), chart) == "0%"


def test_drawable_checks_chart_kind_and_indices() -> None:
    arrow = Annotation("difference", 0, 2)
    assert drawable(arrow, YEARS, "column")
    assert drawable(arrow, YEARS, "mekko")
    assert drawable(arrow, YEARS, "pie")
    assert drawable(arrow, YEARS, "scatter")
    assert not drawable(arrow, YEARS, "area")
    assert not drawable(Annotation("difference", 0, 3), YEARS, "column")
    assert not drawable(Annotation("difference", 3, 0), YEARS, "column")
    assert not drawable(Annotation("difference", 0, 1, series=2), YEARS, "column")
    assert drawable(Annotation("difference", 0, 1, series=1), YEARS, "column")
    assert not drawable(Annotation("difference", 0, 1, series=0, series_end=2), YEARS, "column")
    assert drawable(Annotation("difference", 0, 1, series=0, series_end=1), YEARS, "column")
    assert not drawable(Annotation("group_bracket", 0, 2), YEARS, "line")
    assert drawable(Annotation("group_bracket", 0, 2), YEARS, "column")


def test_from_query_with_defaults() -> None:
    assert from_query("kind=difference&start=0&end=2") == Annotation("difference", 0, 2)


def test_from_query_with_all_arguments() -> None:
    query = "kind=difference&start=1&end=0&series=2&style=level&label=absolute"
    assert from_query(query) == Annotation("difference", 1, 0, 2, "level", "absolute")


def test_from_query_axis_break_is_automatic_without_a_range() -> None:
    assert from_query("kind=axis_break") == Annotation("axis_break", 0, 0)


def test_from_query_axis_break_with_a_range() -> None:
    assert from_query("kind=axis_break&lower=10&upper=50.5") == Annotation(
        "axis_break", 0, 0, lower=10.0, upper=50.5
    )


@pytest.mark.parametrize(
    "query",
    [
        "",
        "kind=difference",
        "start=0&end=1",
        "kind=difference&start=x&end=1",
        "kind=pie&start=0&end=1",
        "kind=difference&start=0&end=0",
        "kind=difference&start=0&end=-1",
        "kind=axis_break&lower=10",
        "kind=axis_break&lower=50&upper=10",
        "kind=axis_break&lower=x&upper=5",
        "kind=difference&start=0&end=1&lower=1&upper=2",
        "kind=category_gap&start=0&end=2",
        "kind=group_bracket&start=0&end=0",
        "kind=group_bracket&start=0&end=1&text=" + "x" * 81,
        "kind=difference&start=0&end=1&series_end=2",
        "kind=difference&start=0&end=0&series=1&series_end=1",
    ],
)
def test_from_query_rejects_bad_arguments(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        from_query(query)


ARROWS = (Annotation("difference", 0, 1), Annotation("cagr", 0, 2))


def test_changed_sets_label_or_style_of_one_annotation() -> None:
    assert changed(ARROWS, "index=0&label=absolute") == (
        Annotation("difference", 0, 1, label="absolute"),
        ARROWS[1],
    )
    assert changed(ARROWS, "index=0&style=level")[0].style == "level"


def test_removed_drops_one_annotation() -> None:
    assert removed(ARROWS, "index=1") == ARROWS[:1]
    assert removed(ARROWS, "index=0") == ARROWS[1:]


@pytest.mark.parametrize(
    "query", ["", "index=2", "index=-1", "index=x", "index=0&label=roman", "index=0&style=curly"]
)
def test_changed_rejects_bad_arguments(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(ARROWS, query)


def test_added_appends_arrows_and_replaces_the_axis_break() -> None:
    arrow, first, second = (
        Annotation("difference", 0, 1),
        Annotation("axis_break", 0, 0),
        Annotation("axis_break", 0, 0, lower=10.0, upper=50.0),
    )
    assert added((arrow,), first) == (arrow, first)
    assert added((first, arrow), second) == (arrow, second)
    assert added((arrow,), Annotation("cagr", 0, 1)) == (arrow, Annotation("cagr", 0, 1))


def test_changed_sets_or_clears_the_range_of_an_axis_break() -> None:
    notes = (Annotation("axis_break", 0, 0),)
    manual = changed(notes, "index=0&lower=10&upper=50")
    assert manual == (Annotation("axis_break", 0, 0, lower=10.0, upper=50.0),)
    assert changed(manual, "index=0&lower=&upper=") == notes
    assert changed(manual, "index=0&label=absolute")[0].upper == 50.0  # range untouched


def test_changed_sets_the_text_of_a_group_bracket() -> None:
    brackets = (Annotation("group_bracket", 0, 2, text="Phase 1"),)
    assert changed(brackets, "index=0&text=Phase%20one") == (
        Annotation("group_bracket", 0, 2, text="Phase one"),
    )


def test_between_series_arrows_compare_two_series_of_one_category() -> None:
    assert label(Annotation("difference", 0, 0, series=0, series_end=1), YEARS) == "0%"
    assert (
        label(Annotation("difference", 0, 0, series=0, series_end=1, label="absolute"), YEARS)
        == "0"
    )
    assert label(Annotation("difference", 2, 2, series=0, series_end=1), YEARS) == "-100%"
    assert (
        label(Annotation("difference", 2, 2, series=0, series_end=1, label="absolute"), YEARS)
        == "-20"
    )
    assert label(Annotation("difference", 1, 1, series=0, series_end=1), YEARS) == NOT_AVAILABLE


def test_an_arrow_can_change_series_and_category_together() -> None:
    assert label(Annotation("difference", 0, 2, series=0, series_end=1), YEARS) == "-100%"
    # Product B's 2025 level (0) grew from Product A's 2020 level (10): CAGR -100 %
    assert label(Annotation("cagr", 2, 0, series=1, series_end=0), YEARS) == "CAGR -100%"


def test_a_cagr_needs_time_even_between_series() -> None:
    assert label(Annotation("cagr", 0, 0, series=0, series_end=1), YEARS) == (
        "CAGR " + NOT_AVAILABLE
    )


def test_a_scatter_cagr_counts_the_x_distance() -> None:
    data = measured(sample_scatter_state())
    x = (12, 18, 25, 31, 14, 22, 35, 40)
    # 30 -> 42 over 6 x units: (42/30) ** (1/6) - 1 = 5.77 %
    assert label(Annotation("cagr", 0, 1), data, x=x) == "CAGR +5.8%"
    assert label(Annotation("cagr", 1, 0), data, x=x) == "CAGR +5.8%"  # either direction


def test_a_scatter_cagr_falls_back_to_the_point_distance() -> None:
    data = measured(sample_scatter_state())
    assert label(Annotation("cagr", 0, 1), data, x=(5,) * 8) == "CAGR +40%"
    assert label(Annotation("cagr", 0, 1), data) == "CAGR +40%"  # no x: index distance


def test_a_pie_measures_shares_in_percent() -> None:
    data = measured(sample_pie_state())
    assert measured_value(data, 0, 0) == 40.0  # Product A's share of 2024
    assert measured_value(data, 1, 2) == 27.0
    assert measured_value(data, 0, None) == 100.0  # the whole pie
    # Product A vs. Product B in 2024: 40 vs. 35
    assert label(Annotation("difference", 0, 0, series=1, series_end=0), data) == "+14.3%"


def test_a_mekko_measures_segment_values() -> None:
    units = measured(replace(sample_mekko_state(), percent=False))
    assert [s.values for s in units.series] == [
        (40.0, 30.0, 20.0, 4.0),
        (25.0, 45.0, 40.0, 3.0),
        (15.0, 10.0, 30.0, 3.0),
    ]
    assert measured_value(units, 0, None) == 80.0  # Europe's column total
    percent = measured(sample_mekko_state())
    assert percent.series[0].values == (50.0, 100 * 30 / 85, 100 * 20 / 90, 100 * 4 / 10)
    assert measured_value(percent, 0, None) == 100.0


def test_a_percent_mekko_difference_reads_as_percentage_points() -> None:
    percent = measured(sample_mekko_state())
    # Product A's vs. Product B's share of Europe: 50 vs. 31.25
    arrow = Annotation("difference", 0, 0, series=0, series_end=1, label="absolute")
    assert label(arrow, percent) == "-18.75"


def test_category_gaps_and_group_brackets_list_the_drawable_ones() -> None:
    annotations = (
        Annotation("category_gap", 0, 1),
        Annotation("group_bracket", 0, 2, text="Phase 1"),
        Annotation("category_gap", 9, 10),  # past the data: stays stored, is not drawn
        Annotation("difference", 0, 1),
    )
    assert category_gaps(annotations, YEARS, "column") == [annotations[0]]
    assert group_brackets(annotations, YEARS, "column") == [annotations[1]]
    assert category_gaps(annotations, YEARS, "line") == []
    assert category_gaps(annotations, ChartData((), ()), "column") == []


def test_bracket_text_is_validated_for_the_dialog() -> None:
    assert check_bracket_text("  Phase 1 ") is None
    assert check_bracket_text("x" * 80) is None
    assert check_bracket_text("") == "bracket_text_missing"
    assert check_bracket_text("   ") == "bracket_text_missing"
    assert check_bracket_text("x" * 81) == "bracket_text_too_long"


def test_from_query_parses_gaps_brackets_and_series_ends() -> None:
    assert from_query("kind=category_gap&start=1&end=2") == Annotation("category_gap", 1, 2)
    assert from_query("kind=group_bracket&start=0&end=2&text=Phase+1") == Annotation(
        "group_bracket", 0, 2, text="Phase 1"
    )
    assert from_query("kind=difference&start=0&end=0&series=1&series_end=2") == Annotation(
        "difference", 0, 0, series=1, series_end=2
    )
    assert from_query("kind=group_bracket&start=0&end=2") == Annotation("group_bracket", 0, 2)
