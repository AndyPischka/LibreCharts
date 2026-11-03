from dataclasses import replace

import pytest

from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.layout.column import LANE_HEIGHT
from librecharts.core.messages import MESSAGES
from librecharts.core.model import Annotation
from librecharts.core.picking import PickSession, annotation_kind, placed, supports, target_at

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


def test_waterfall_charts_have_targets_by_column() -> None:
    waterfall = sample_waterfall_state()
    assert target_at(waterfall, 3000, 8000, 100, 4000) == (0, None)
    assert target_at(waterfall, 3000, 8000, 2999, 4000) is not None
    assert target_at(waterfall, 3000, 8000, 3000, 4000) is None


def test_bar_charts_have_targets_and_mekko_segments_are_targets() -> None:
    bar = replace(STACKED, kind="bar")
    assert target_at(bar, 12000, 3000, 4000, 100) == (0, None)
    assert target_at(bar, 12000, 3000, 4000, 2900) == (2, None)
    # the sample Mekko: Europe (80 wide of 185 total) starts with Product A's 40 of 80
    assert target_at(sample_mekko_state(), WIDTH, HEIGHT, 500, 500) is None  # above the plot
    assert target_at(sample_mekko_state(), WIDTH, HEIGHT, 500, 5000) == (0, 0)
    assert target_at(sample_mekko_state(), WIDTH, HEIGHT, 500, 3000) == (0, 1)  # Product B
    assert target_at(sample_mekko_state(), WIDTH, HEIGHT, 500, 1500) == (0, 2)  # Product C


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
    assert session.add((1, 2)) is None  # a CAGR needs two different categories
    assert session.add((0, 0)) == Annotation("cagr", 1, 0, series=0)


def test_two_series_of_one_category_make_a_between_series_arrow() -> None:
    session = PickSession("difference")
    session.add((1, 0))
    assert session.add((1, 2)) == Annotation("difference", 1, 1, series=0, series_end=2)


def test_bars_of_different_series_measure_those_series() -> None:
    session = PickSession("difference", style="level")
    session.add((0, 0))
    assert session.add((1, 2)) == Annotation(
        "difference", 0, 1, series=0, style="level", series_end=2
    )


def test_a_gap_session_needs_adjacent_categories() -> None:
    session = PickSession("gap")
    assert session.prompt == "pick_gap_start"
    assert session.add((0, None)) is None
    assert session.prompt == "pick_gap_end"
    assert session.add((2, None)) is None  # not adjacent: ignored
    assert session.add((1, None)) == Annotation("category_gap", 0, 1)
    assert PickSession.from_query("kind=gap").prompt == "pick_gap_start"


def test_a_bracket_session_spans_two_categories_in_any_order() -> None:
    session = PickSession("bracket")
    assert session.prompt == "pick_bracket_start"
    assert session.add((2, 1)) is None  # the series of a pick is ignored
    assert session.prompt == "pick_bracket_end"
    assert session.add((0, None)) == Annotation("group_bracket", 0, 2)


def test_supports_follows_the_chart_kind() -> None:
    assert supports(STACKED, "difference")
    assert supports(STACKED, "axis_break")
    assert supports(sample_mekko_state(), "difference")  # percent Mekko: percentage points
    assert supports(replace(sample_mekko_state(), percent=False), "cagr")


def test_a_100_percent_chart_offers_no_annotations() -> None:
    percent = replace(STACKED, percent=True)
    assert not supports(percent, "difference")
    assert not supports(percent, "axis_break")
    percent_mekko = replace(sample_mekko_state(), percent=True)
    assert supports(percent_mekko, "difference")  # its segment levels are percentage points
    assert not supports(percent_mekko, "cagr")


def test_session_kinds_map_to_annotation_kinds() -> None:
    assert annotation_kind("difference") == "difference"
    assert annotation_kind("cagr") == "cagr"
    assert annotation_kind("gap") == "category_gap"
    assert annotation_kind("bracket") == "group_bracket"


def test_a_between_series_bradket_needs_side_by_side_bars() -> None:
    between = Annotation("difference", 1, 1, series=0, series_end=1)
    assert placed(replace(STACKED, grouping="clustered"), between) == between
    assert placed(STACKED, between) == Annotation(
        "difference", 1, 1, series=0, series_end=1, style="level"
    )
    # charts that stack their series measure levels instead
    assert placed(replace(STACKED, kind="line"), between).style == "level"
    assert placed(sample_mekko_state(), between).style == "level"
    assert placed(replace(STACKED, kind="bar", grouping="clustered"), between).style == "bracket"


def test_a_between_series_level_arrow_on_a_pie_becomes_a_bracket() -> None:
    pie = replace(sample_state(), kind="pie")
    between = Annotation("difference", 1, 1, series=0, series_end=1, style="level")
    assert placed(pie, between) == Annotation("difference", 1, 1, series=0, series_end=1)
    # an arrow over categories keeps the style it was picked with
    across = Annotation("difference", 0, 2, style="level")
    assert placed(pie, across) == across
    assert placed(STACKED, across) == across


def test_a_sorted_chart_reports_the_data_sheet_index() -> None:
    # descending: display order 2025, 2024, 2023 -> data indices 2, 1, 0
    sorted_state = replace(STACKED, sort="descending")
    assert target_at(sorted_state, WIDTH, HEIGHT, 500, 5000) == (2, None)
    assert target_at(sorted_state, WIDTH, HEIGHT, 1500, 5000) == (1, None)
    assert target_at(sorted_state, WIDTH, HEIGHT, 2500, 5000) == (0, None)


def test_session_from_query() -> None:
    assert PickSession.from_query("kind=cagr") == PickSession("cagr")
    assert PickSession.from_query("kind=difference&style=level") == PickSession(
        "difference", "level"
    )
    assert PickSession.from_query("kind=gap") == PickSession("gap")
    assert PickSession.from_query("kind=bracket") == PickSession("bracket")


@pytest.mark.parametrize(
    "query", ["", "kind=pie", "kind=axis_break", "kind=difference&style=curly"]
)
def test_session_from_bad_query_is_rejected(query: str) -> None:
    with pytest.raises(ValueError, match="unknown"):
        PickSession.from_query(query)


def test_every_prompt_has_a_message() -> None:
    for session in (
        PickSession("difference"),
        PickSession("cagr"),
        PickSession("gap"),
        PickSession("bracket"),
    ):
        assert session.prompt in MESSAGES
        session.add((0, None))
        assert session.prompt in MESSAGES


def test_level_lanes_right_of_the_plot_hit_nothing() -> None:
    level = replace(STACKED, annotations=(Annotation("difference", 0, 1, style="level"),))
    # the plot shrinks to 3000 - LEVEL_LANE_WIDTH = 1000: slots of 333
    assert target_at(level, WIDTH, HEIGHT, 500, 5000) == (1, None)
    assert target_at(level, WIDTH, HEIGHT, 1500, 5000) is None


LINE = state_from_table("line", "stacked", [[None, "2020", "2021"], ["Sales", 10, 20]])
AREA = state_from_table("area", "stacked", [[None, "2020", "2021"], ["Sales", 10, 20]])


def test_line_points_are_targets() -> None:
    # axis 0..20 over 8200 from y=800: 10 is at 4900, 20 at 800; slots of 1000
    assert target_at(LINE, 2000, 10000, 500, 4900) == (0, 0)
    assert target_at(LINE, 2000, 10000, 1500, 800) == (1, 0)
    assert target_at(LINE, 2000, 10000, 500, 4000) == (0, 0)  # within the tolerance


def test_a_click_far_from_every_line_point_hits_nothing() -> None:
    assert target_at(LINE, 2000, 10000, 500, 9000) is None
    assert target_at(LINE, 2000, 10000, 2500, 4900) is None
    assert target_at(LINE, 2000, 10000, 500, 100) is None


def test_area_charts_have_no_targets() -> None:
    assert target_at(AREA, 2000, 10000, 500, 4900) is None


def test_a_series_drawn_as_a_line_can_be_picked() -> None:
    state = replace(STACKED, lines=(2,))
    # line series C: 5, 8 and 9; the axis stays 0..40 (column totals), plot 6200 high from 800
    assert target_at(state, WIDTH, HEIGHT, 500, 800 + (40 - 5) / 40 * 6200) == (0, 2)
    assert target_at(state, WIDTH, HEIGHT, 1500, 800 + (40 - 8) / 40 * 6200) == (1, 2)


def test_secondary_line_points_use_the_secondary_scale() -> None:
    state = replace(STACKED, lines=(2,), secondary=(2,))
    # the right axis covers the line values only (0..10) and takes one axis band of the plot
    assert target_at(state, WIDTH, HEIGHT, 700, 800 + (10 - 8) / 10 * 6200) == (1, 2)
