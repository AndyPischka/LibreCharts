import pytest

from librecharts.core.datasheet import (
    ChartData,
    Series,
    sample_scatter_state,
    sample_state,
    sample_waterfall_state,
)
from librecharts.core.model import Annotation
from librecharts.core.value_line import (
    average,
    average_for,
    check,
    median,
    resolved,
    statistic,
    statistic_for,
)


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def test_the_average_is_the_mean_of_the_column_sums() -> None:
    chart = data(("A", (10.0, 0.0)), ("B", (30.0, 20.0)), categories=("X", "Y"))
    assert average(chart) == pytest.approx((40 + 20) / 2)


def test_empty_cells_do_not_count() -> None:
    chart = data(("A", (10.0, None)), ("B", (None, 20.0)), categories=("X", "Y"))
    assert average(chart) == pytest.approx(15.0)


def test_negative_values_reduce_the_sum() -> None:
    chart = data(("A", (10.0,)), ("B", (-4.0,)), categories=("X",))
    assert average(chart) == pytest.approx(6.0)


def test_without_categories_there_is_no_average() -> None:
    assert average(ChartData((), ())) is None


def test_the_average_of_a_column_chart_comes_from_its_state() -> None:
    # 2023: 35, 2024: 42, 2025: 45
    assert average_for(sample_state()) == pytest.approx((35 + 42 + 45) / 3)


def test_the_average_of_a_waterfall_is_the_mean_of_the_step_levels() -> None:
    # the bridge starts at 100 and ends at 110, every step's end level counts once
    assert average_for(sample_waterfall_state()) == pytest.approx(
        (100 + 130 + 145 + 120 + 110 + 110) / 6
    )


def test_a_value_line_uses_its_value_or_the_average() -> None:
    chart = data(("A", (10.0,)), categories=("X",))
    assert resolved(Annotation("value_line", 0, 0, value=5.0), chart) == 5.0
    assert resolved(Annotation("value_line", 0, 0), chart) == pytest.approx(10.0)


def test_the_median_is_the_middle_column_sum() -> None:
    chart = data(("A", (10.0, 0.0, 5.0)), ("B", (30.0, 20.0, 0.0)), categories=("X", "Y", "Z"))
    assert median(chart) == pytest.approx(20.0)  # the sums are 40, 20, 5


def test_an_even_number_of_sums_takes_the_mean_of_the_two_middle_ones() -> None:
    chart = data(("A", (1.0, 2.0, 3.0, 10.0)), categories=("W", "X", "Y", "Z"))
    assert median(chart) == pytest.approx(2.5)


def test_the_median_ignores_empty_cells_and_counts_negative_sums() -> None:
    chart = data(("A", (10.0, None)), ("B", (None, -4.0)), categories=("X", "Y"))
    assert median(chart) == pytest.approx(3.0)  # the sums are 10, -4


def test_without_categories_there_is_no_median() -> None:
    assert median(ChartData((), ())) is None


def test_statistic_dispatches_on_the_mode() -> None:
    chart = data(("A", (1.0, 2.0, 3.0, 10.0)), categories=("W", "X", "Y", "Z"))
    assert statistic(chart, None) == pytest.approx(4.0)
    assert statistic(chart, "average") == pytest.approx(4.0)
    assert statistic(chart, "median") == pytest.approx(2.5)


def test_the_median_of_a_column_chart_comes_from_its_state() -> None:
    # 2023: 35, 2024: 42, 2025: 45
    assert statistic_for(sample_state(), "median") == pytest.approx(42.0)


def test_the_median_of_a_waterfall_is_the_middle_step_level() -> None:
    # the levels are 100, 130, 145, 120, 110, 110; sorted: 100, 110, 110, 120, 130, 145
    assert statistic_for(sample_waterfall_state(), "median") == pytest.approx(115.0)


def test_the_median_of_a_scatter_is_the_middle_y_value() -> None:
    state = sample_scatter_state()
    ys = sorted([30, 42, 38, 55, 18, 25, 33, 48])
    assert statistic_for(state, "median") == pytest.approx((ys[3] + ys[4]) / 2)


def test_a_value_line_uses_its_value_or_the_statistic_of_its_mode() -> None:
    chart = data(("A", (1.0, 2.0, 3.0, 10.0)), categories=("W", "X", "Y", "Z"))
    line = Annotation("value_line", 0, 0)
    assert resolved(line, chart) == pytest.approx(4.0)  # the average by default
    average = Annotation("value_line", 0, 0, value_line_mode="average")
    median = Annotation("value_line", 0, 0, value_line_mode="median")
    assert resolved(average, chart) == pytest.approx(4.0)
    assert resolved(median, chart) == pytest.approx(2.5)
    # an explicit value wins over any statistic
    assert resolved(Annotation("value_line", 0, 0, value=5.0), chart) == 5.0
    valued = Annotation("value_line", 0, 0, value=5.0, value_line_mode="median")
    assert resolved(valued, chart) == 5.0


def test_the_average_mode_is_the_default_and_other_modes_are_rejected() -> None:
    assert Annotation("value_line", 0, 0, value_line_mode="average").value_line_mode is None
    with pytest.raises(ValueError, match="unknown value line mode"):
        Annotation("value_line", 0, 0, value_line_mode="middle")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="only a value line has a mode"):
        Annotation("difference", 0, 1, value_line_mode="median")


@pytest.mark.parametrize(("text", "value"), [("42", 42.0), (" 4,5 ", 4.5), ("-3", -3.0)])
def test_the_value_field_accepts_numbers(text: str, value: float) -> None:
    assert check(text) == value


@pytest.mark.parametrize("text", ["", "abc", "1,2,3", "inf", "nan"])
def test_the_value_field_rejects_anything_else(text: str) -> None:
    assert check(text) == "value_line_not_a_number"
