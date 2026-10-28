import math

import pytest

from librecharts.core.scale import Axis, nice_axis


def test_rounds_up_to_nice_maximum() -> None:
    assert nice_axis(0, 97) == Axis(0, 100, 20)


def test_negative_values_include_zero_baseline() -> None:
    assert nice_axis(-30, 80) == Axis(-50, 100, 50)


def test_without_zero_baseline() -> None:
    assert nice_axis(3, 17, include_zero=False) == Axis(0, 20, 5)


def test_small_values_have_no_float_noise() -> None:
    axis = nice_axis(0, 0.3)
    assert axis.maximum == pytest.approx(0.3)
    assert axis.step == pytest.approx(0.1)
    assert axis.ticks() == pytest.approx([0, 0.1, 0.2, 0.3])


def test_degenerate_range_still_yields_valid_axis() -> None:
    axis = nice_axis(0, 0)
    assert axis.step > 0
    assert axis.maximum > axis.minimum


def test_ticks_cover_range_inclusively() -> None:
    assert Axis(0, 100, 25).ticks() == [0, 25, 50, 75, 100]


@pytest.mark.parametrize(
    ("low", "high", "max_ticks"),
    [(math.nan, 1, 6), (0, math.inf, 6), (5, 1, 6), (0, 1, 1)],
)
def test_invalid_input_is_rejected(low: float, high: float, max_ticks: int) -> None:
    with pytest.raises(ValueError, match="must"):
        nice_axis(low, high, max_ticks)
