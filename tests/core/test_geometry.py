import math

import pytest

from librecharts.core.geometry import POINTS_PER_DEGREE, polar, sector


def test_angles_run_clockwise_from_twelve_o_clock() -> None:
    assert polar(0, 0, 10, 0) == pytest.approx((0, -10))
    assert polar(0, 0, 10, 90) == pytest.approx((10, 0))
    assert polar(0, 0, 10, 180) == pytest.approx((0, 10))
    assert polar(5, 5, 10, 270) == pytest.approx((-5, 5))


def test_a_pie_segment_starts_at_the_centre_and_follows_the_arc() -> None:
    points = sector(100, 100, 50, 0, 0, 90)
    assert points[0] == (100, 100)
    assert points[1] == pytest.approx((100, 50))
    assert points[-1] == pytest.approx((150, 100))
    assert len(points) == 1 + 90 * POINTS_PER_DEGREE + 1
    assert all(math.hypot(x - 100, y - 100) == pytest.approx(50) for x, y in points[1:])


def test_a_doughnut_segment_goes_out_along_the_arc_and_back_along_the_inner_one() -> None:
    points = sector(0, 0, 100, 40, 0, 90)
    count = 90 * POINTS_PER_DEGREE + 1
    assert len(points) == 2 * count
    assert [round(math.hypot(x, y)) for x, y in points[:count]] == [100] * count
    assert [round(math.hypot(x, y)) for x, y in points[count:]] == [40] * count
    assert points[count] == pytest.approx((40, 0))  # the inner arc starts where the outer ended


def test_the_point_count_depends_on_the_sweep_and_not_on_the_radius() -> None:
    assert len(sector(0, 0, 10, 0, 0, 120)) == len(sector(0, 0, 9999, 0, 0, 120))
    assert len(sector(0, 0, 10, 5, 0, 120)) == len(sector(0, 0, 9999, 5, 0, 120))


def test_a_tiny_sweep_still_has_two_arc_points() -> None:
    assert len(sector(0, 0, 10, 0, 10, 10.2)) == 3


@pytest.mark.parametrize(
    ("outer", "inner", "start", "end"),
    [(0, 0, 0, 10), (10, 10, 0, 10), (10, -1, 0, 10), (10, 11, 0, 10), (10, 0, 20, 10)],
)
def test_invalid_sectors_are_rejected(outer: float, inner: float, start: float, end: float) -> None:
    with pytest.raises(ValueError, match=r"."):
        sector(0, 0, outer, inner, start, end)
