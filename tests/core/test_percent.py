import pytest

from librecharts.core.datasheet import ChartData, Series
from librecharts.core.percent import column_total, positive_only, share, share_label, shares


def data(*series: tuple[str, tuple[float | None, ...]]) -> ChartData:
    return ChartData(("A", "B", "C"), tuple(Series(n, v) for n, v in series))


def test_negative_and_zero_values_count_as_empty() -> None:
    chart = positive_only(data(("S", (10.0, -5.0, 0.0))))
    assert chart.series[0].values == (10.0, None, None)


def test_column_total_adds_only_positive_values() -> None:
    chart = data(("A", (10.0, -5.0, 2.0)), ("B", (30.0, 3.0, None)))
    assert column_total(chart, 0) == 40.0
    assert column_total(chart, 1) == 3.0
    assert column_total(chart, 2) == 2.0


def test_share_is_a_percentage_or_none() -> None:
    assert share(10.0, 40.0) == 25.0
    assert share(None, 40.0) is None
    assert share(-1.0, 40.0) is None
    assert share(1.0, 0.0) is None


@pytest.mark.parametrize(
    ("value", "label"),
    [(10.0, "25%"), (5.0, "12.5%"), (40.0 / 3, "33.3%"), (None, "")],
)
def test_share_labels(value: float | None, label: str) -> None:
    assert share_label(value, 40.0) == label


def test_shares_replaces_values_by_their_column_share() -> None:
    chart = shares(data(("A", (10.0, 5.0, 0.0)), ("B", (30.0, None, 1.0))))
    assert chart.series[0].values == (25.0, 100.0, None)
    assert chart.series[1].values == (75.0, None, 100.0)


def test_an_empty_column_has_no_shares() -> None:
    chart = shares(data(("A", (None, None, None))))
    assert chart.series[0].values == (None, None, None)
