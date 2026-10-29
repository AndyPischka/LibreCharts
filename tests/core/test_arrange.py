import pytest

from librecharts.core import arrange


def test_same_width_height_and_size_use_the_largest() -> None:
    rects = [(0, 0, 100, 50), (200, 10, 300, 20)]
    assert arrange.same_width(rects) == [(0, 0, 300, 50), (200, 10, 300, 20)]
    assert arrange.same_height(rects) == [(0, 0, 100, 50), (200, 10, 300, 50)]
    assert arrange.same_size(rects) == [(0, 0, 300, 50), (200, 10, 300, 50)]
    assert arrange.same_size([]) == []


def test_grid_keeps_the_top_left_and_leaves_equal_gaps() -> None:
    rects = [(500, 400, 100, 100), (900, 400, 100, 100), (500, 900, 100, 100), (900, 900, 100, 100)]
    assert arrange.grid(rects, 2, 20) == [
        (500, 400, 100, 100),
        (620, 400, 100, 100),
        (500, 520, 100, 100),
        (620, 520, 100, 100),
    ]


def test_grid_with_a_partial_last_row_and_input_order_kept() -> None:
    rects = [(300, 300, 50, 50), (0, 0, 50, 50), (100, 0, 50, 50)]  # reading order: 1, 2, 0
    assert arrange.grid(rects, 2, 10) == [(0, 60, 50, 50), (0, 0, 50, 50), (60, 0, 50, 50)]


def test_grid_columns_are_as_wide_as_their_widest_shape() -> None:
    rects = [(0, 0, 100, 40), (200, 0, 50, 80), (0, 200, 60, 30), (200, 200, 70, 30)]
    placed = arrange.grid(rects, 2, 10)
    assert placed[1][:2] == (110, 0)  # after the 100 wide first column
    assert placed[2][:2] == (0, 90)  # after the 80 high first row


def test_grid_rejects_bad_arguments() -> None:
    with pytest.raises(ValueError, match="grid"):
        arrange.grid([(0, 0, 1, 1)], 0, 0)
    with pytest.raises(ValueError, match="grid"):
        arrange.grid([(0, 0, 1, 1)], 1, -1)
    assert arrange.grid([], 2, 0) == []


def test_swap_exchanges_centres_and_keeps_sizes() -> None:
    first, second = arrange.swap((0, 0, 100, 100), (400, 200, 200, 50))
    assert first == (450, 175, 100, 100)  # centre of the second: (500, 225)
    assert second == (-50, 25, 200, 50)  # centre of the first: (50, 50)
