from dataclasses import replace

import pytest

from librecharts.core.datasheet import sample_mekko_state, sample_state
from librecharts.core.layout.column import LANE_HEIGHT
from librecharts.core.messages import MESSAGES
from librecharts.core.model import Annotation
from librecharts.core.picking import PickSession, supports, target_at

STACKED = sample_state()  # three categories, three series
CLUSTERED = replace(STACKED, grouping="clustered")
WIDTH = 3000.0  # slots of 1000, columns of 700 from 150 to 850, clustered bars ~233 wide
HEIGHT = 8000.0


@pytest.mark.parametrize(
    ("x", "target"), [(0, (0, None)), (500, (0, None)), (1500, (1, None)), (2999, (2, None))]
)
def test_stacked_targets_are_whole_columns(x: float, target: tuple[int, None]) -> None:
    assert target_at(STACKED, WIDTH, HEIGHT, x, 5000) == target


@pytest.mark.parametrize(
    ("x", "target"),
    [(200, (0, 0)), (500, (0, 1)), (800, (0, 2)), (1100, (1, None)), (2900, (2, None))],
)
def test_clustered_targets_are_single_bars_or_the_column(
    x: float, target: tuple[int, int | None]
) -> None:
    assert target_at(CLUSTERED, WIDTH, HEIGHT, x, 5000) == target


def test_points_outside_the_box_or_in_arrow_lanes_hit_nothing() -> None:
    assert target_at(STACKED, WIDTH, HEIGHT, -1, 5000) is None
    assert target_at(STACKED, WIDTH, HEIGHT, WIDTH, 5000) is None
    with_arrow = replace(STACKED, annotations=(Annotation("difference", 0, 1),))
    assert target_at(with_arrow, WIDTH, HEIGHT, 500, LANE_HEIGHT - 1) is None
    assert target_at(with_arrow, WIDTH, HEIGHT, 500, LANE_HEIGHT) == (0, None)


def test_bar_charts_have_targets_and_other_charts_do_not() -> None:
    bar = replace(STACKED, kind="bar")
    assert target_at(bar, 12000, 3000, 4000, 100) == (0, None)
    assert target_at(bar, 12000, 3000, 4000, 2900) == (2, None)
    assert target_at(sample_mekko_state(), WIDTH, HEIGHT, 500, 5000) is None


def test_empty_chart_has_no_targets() -> None:
    empty = replace(STACKED, cells=(("",),), values=((None,),))
    assert target_at(empty, WIDTH, HEIGHT, 500, 5000) is None


def test_session_asks_for_start_then_end_and_returns_the_arrow() -> None:
    session = PickSession("difference")
    assert session.prompt == "pick_start"
    assert session.add((0, None)) is None
    assert session.prompt == "pick_end"
    assert session.add((2, None)) == Annotation("difference", 0, 2)


def test_picking_the_start_column_again_is_ignored() -> None:
    session = PickSession("cagr")
    session.add((1, 0))
    assert session.add((1, 2)) is None
    assert session.add((0, 0)) == Annotation("cagr", 1, 0, series=0)


def test_bars_of_different_series_measure_column_totals() -> None:
    session = PickSession("difference", style="level")
    session.add((0, 0))
    assert session.add((1, 2)) == Annotation("difference", 0, 1, style="level")


def test_supports_follows_the_chart_kind() -> None:
    assert supports(STACKED, "difference")
    assert supports(STACKED, "axis_break")
    assert not supports(sample_mekko_state(), "difference")


def test_session_from_query() -> None:
    assert PickSession.from_query("kind=cagr") == PickSession("cagr")
    assert PickSession.from_query("kind=difference&style=level") == PickSession(
        "difference", "level"
    )


@pytest.mark.parametrize(
    "query", ["", "kind=pie", "kind=axis_break", "kind=difference&style=curly"]
)
def test_session_from_bad_query_is_rejected(query: str) -> None:
    with pytest.raises(ValueError, match="unknown"):
        PickSession.from_query(query)


def test_every_prompt_has_a_message() -> None:
    for session in (PickSession("difference"), PickSession("cagr")):
        assert session.prompt in MESSAGES
        session.add((0, None))
        assert session.prompt in MESSAGES


def test_level_lanes_right_of_the_plot_hit_nothing() -> None:
    level = replace(STACKED, annotations=(Annotation("difference", 0, 1, style="level"),))
    # the plot shrinks to 3000 - LEVEL_LANE_WIDTH = 1000: slots of 333
    assert target_at(level, WIDTH, HEIGHT, 500, 5000) == (1, None)
    assert target_at(level, WIDTH, HEIGHT, 1500, 5000) is None
