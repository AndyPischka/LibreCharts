import pytest

from librecharts.core.axis_break import (
    KEEP,
    SHOW,
    Break,
    automatic,
    check,
    column_tops,
    describe,
    resolve,
)
from librecharts.core.datasheet import ChartData, Series
from librecharts.core.model import Annotation

DATA = ChartData(
    ("A", "B", "C"), (Series("S", (10.0, 100.0, 20.0)), Series("T", (5.0, -3.0, None)))
)


def test_fold_keeps_values_below_and_shifts_values_above_the_removed_range() -> None:
    cut = Break(30.0, 60.0)
    assert [cut.fold(v) for v in (0.0, 30.0, 45.0, 59.9, 60.0, 100.0)] == [
        0.0,
        30.0,
        30.0,
        30.0,
        30.0,
        70.0,
    ]


def test_a_column_is_cut_when_it_reaches_beyond_the_lower_value() -> None:
    cut = Break(30.0, 60.0)
    assert cut.cuts(30.1)
    assert not cut.cuts(30.0)


def test_column_tops_ignore_negative_values_and_gaps() -> None:
    assert column_tops(DATA, "stacked") == [15.0, 100.0, 20.0]
    assert column_tops(DATA, "clustered") == [10.0, 100.0, 20.0]


def test_automatic_break_leaves_the_second_tallest_column_alone() -> None:
    cut = automatic([10.0, 100.0, 20.0])
    assert cut is not None
    assert cut.lower == pytest.approx(KEEP * 20)
    assert cut.fold(20.0) == 20.0
    assert cut.fold(100.0) == pytest.approx(SHOW * 20)  # the tallest continues up to here


@pytest.mark.parametrize("tops", [[], [50.0], [10.0, 12.0], [0.0, 50.0], [20.0, 25.0, 20.0]])
def test_no_automatic_break_unless_one_column_dwarfs_the_rest(tops: list[float]) -> None:
    assert automatic(tops) is None


def test_resolve_uses_the_last_axis_break() -> None:
    first = Annotation("axis_break", 0, 0, lower=10.0, upper=20.0)
    last = Annotation("axis_break", 0, 0, lower=30.0, upper=60.0)
    assert resolve((first, Annotation("difference", 0, 1), last), DATA, "stacked") == Break(30, 60)


def test_resolve_without_an_axis_break_or_data_is_none() -> None:
    assert resolve((Annotation("difference", 0, 1),), DATA, "stacked") is None
    assert resolve((Annotation("axis_break", 0, 0),), ChartData((), ()), "stacked") is None


def test_resolve_automatic_follows_the_data() -> None:
    assert resolve((Annotation("axis_break", 0, 0),), DATA, "stacked") == automatic(
        [15.0, 100.0, 20.0]
    )


def test_a_manual_break_that_no_column_reaches_is_not_drawn() -> None:
    manual = Annotation("axis_break", 0, 0, lower=30.0, upper=200.0)
    assert resolve((manual,), DATA, "stacked") is None


@pytest.mark.parametrize(
    ("annotation", "text"),
    [
        (Annotation("axis_break", 0, 0), "auto"),
        (Annotation("axis_break", 0, 0, lower=10.0, upper=50.5), "10-50.5"),
    ],
)
def test_describe(annotation: Annotation, text: str) -> None:
    assert describe(annotation) == text


@pytest.mark.parametrize(
    ("lower", "upper", "expected"),
    [
        ("10", "50", (10.0, 50.0)),
        (" 10,5 ", "50.25", (10.5, 50.25)),
        ("0", "100", (0.0, 100.0)),
        ("", "5", "break_not_a_number"),
        ("a", "5", "break_not_a_number"),
        ("nan", "5", "break_not_a_number"),
        ("inf", "5", "break_not_a_number"),
        ("-1", "5", "break_order"),
        ("50", "50", "break_order"),
        ("60", "50", "break_order"),
        ("10", "100.5", "break_too_high"),
    ],
)
def test_check(lower: str, upper: str, expected: tuple[float, float] | str) -> None:
    assert check(lower, upper, tallest=100.0) == expected
