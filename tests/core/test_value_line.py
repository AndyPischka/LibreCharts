import pytest

from librecharts.core.datasheet import ChartData, Series, sample_state, sample_waterfall_state
from librecharts.core.model import Annotation
from librecharts.core.value_line import average, average_for, check, resolved


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


@pytest.mark.parametrize(("text", "value"), [("42", 42.0), (" 4,5 ", 4.5), ("-3", -3.0)])
def test_the_value_field_accepts_numbers(text: str, value: float) -> None:
    assert check(text) == value


@pytest.mark.parametrize("text", ["", "abc", "1,2,3", "inf", "nan"])
def test_the_value_field_rejects_anything_else(text: str) -> None:
    assert check(text) == "value_line_not_a_number"
