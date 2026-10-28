import pytest

from librecharts.core.annotations import (
    NOT_AVAILABLE,
    changed,
    drawable,
    from_query,
    label,
    measured_value,
    removed,
)
from librecharts.core.datasheet import ChartData, Series
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
    assert not drawable(arrow, YEARS, "mekko")
    assert not drawable(Annotation("difference", 0, 3), YEARS, "column")
    assert not drawable(Annotation("difference", 3, 0), YEARS, "column")
    assert not drawable(Annotation("difference", 0, 1, series=2), YEARS, "column")
    assert drawable(Annotation("difference", 0, 1, series=1), YEARS, "column")


def test_from_query_with_defaults() -> None:
    assert from_query("kind=difference&start=0&end=2") == Annotation("difference", 0, 2)


def test_from_query_with_all_arguments() -> None:
    query = "kind=difference&start=1&end=0&series=2&style=level&label=absolute"
    assert from_query(query) == Annotation("difference", 1, 0, 2, "level", "absolute")


def test_from_query_axis_break_needs_no_end() -> None:
    assert from_query("kind=axis_break&start=1") == Annotation("axis_break", 1, 1)


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
