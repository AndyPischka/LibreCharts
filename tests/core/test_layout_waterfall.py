from dataclasses import replace

import pytest

from librecharts.core.datasheet import sample_waterfall_state, state_from_table
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.column import (
    BREAK_GAP,
    BREAK_OVERHANG,
    LANE_HEIGHT,
    LANE_LINE_GAP,
    LEVEL_ARROW_INSET,
    LEVEL_LANE_WIDTH,
)
from librecharts.core.layout.waterfall import (
    CATEGORY_BAND,
    LABEL_HEIGHT,
    TOP_BAND,
    layout_waterfall,
    step_at,
)
from librecharts.core.model import Annotation
from librecharts.core.primitives import BACKGROUND, Line, Rect, Text
from librecharts.core.waterfall import Step, WaterfallData, parse_waterfall


def test_golden_geometry() -> None:
    # levels 0..100; the fall reserves 600 below the plot: y(100)=800, y(60)=3840, y(0)=8400
    data = WaterfallData(
        (
            Step("A", 0, 100, True, True),
            Step("B", 100, 60, False, True),
            Step("C", 0, 60, True, True),
        )
    )
    assert layout_waterfall(data, 3000, 10000) == (
        Line(0, 8400, 3000, 8400, "baseline"),
        Rect(150, 800, 700, 7600, 0),
        Text(150, 200, 700, LABEL_HEIGHT, "100", "center", "value"),
        Line(850, 800, 1150, 800, "connector"),
        Text(0, 9000, 1000, CATEGORY_BAND, "A", "center", "category"),
        Rect(1150, 800, 700, 3040, 2),
        Text(1150, 3840, 700, LABEL_HEIGHT, "-40", "center", "value"),
        Line(1850, 3840, 2150, 3840, "connector"),
        Text(1000, 9000, 1000, CATEGORY_BAND, "B", "center", "category"),
        Rect(2150, 3840, 700, 4560, 0),
        Text(2150, 3240, 700, LABEL_HEIGHT, "60", "center", "value"),
        Text(2000, 9000, 1000, CATEGORY_BAND, "C", "center", "category"),
    )


def test_rises_are_signed_and_use_their_own_colour_index() -> None:
    data = WaterfallData((Step("A", 0, 10, True, True), Step("B", 10, 15, False, True)))
    primitives = layout_waterfall(data, 2000, 10000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    assert [r.series for r in rects] == [0, 1]
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["10", "+5"]


def test_a_gap_has_an_empty_label_and_no_height() -> None:
    data = WaterfallData((Step("A", 0, 10, True, True), Step("Gap", 10, 10, False, False)))
    primitives = layout_waterfall(data, 2000, 10000)
    gap = [p for p in primitives if isinstance(p, Rect)][1]
    assert gap.height == 0
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["10", ""]


def test_negative_levels_hang_below_the_baseline() -> None:
    data = WaterfallData((Step("A", 0, -20, True, True),))
    primitives = layout_waterfall(data, 1000, 10000)
    baseline = next(p for p in primitives if isinstance(p, Line))
    rect = next(p for p in primitives if isinstance(p, Rect))
    label = next(p for p in primitives if isinstance(p, Text) and p.role == "value")
    assert rect.y == pytest.approx(baseline.y1)
    assert label.y == pytest.approx(rect.y + rect.height)
    category = next(p for p in primitives if isinstance(p, Text) and p.role == "category")
    assert label.y + label.height <= category.y + 1e-9


def test_connectors_join_the_end_of_a_column_to_the_start_of_the_next() -> None:
    primitives = layout_chart(sample_waterfall_state(), 24000, 12000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    connectors = [p for p in primitives if isinstance(p, Line) and p.role == "connector"]
    assert len(connectors) == len(rects) - 1
    for rect, nxt, line in zip(rects, rects[1:], connectors, strict=False):
        assert line.x1 == pytest.approx(rect.x + rect.width)
        assert line.x2 == pytest.approx(nxt.x)
        assert line.y1 == line.y2


def test_all_geometry_stays_inside_the_box() -> None:
    for p in layout_chart(sample_waterfall_state(), 24000, 12000):
        if isinstance(p, Rect | Text):
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9


def test_structure_does_not_depend_on_size() -> None:
    state = state_from_table(
        "waterfall",
        "stacked",
        [
            [None, "A", "B", "C", "D"],
            ["Value", 100, -300, None, 7],
            ["Total", "x", None, None, "x"],
        ],
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", "")) for p in layout_chart(state, width, height)
        ]

    assert shape(4000, 3000) == shape(30000, 20000) == shape(900, 2500)


def test_empty_data_yields_nothing() -> None:
    assert layout_waterfall(WaterfallData(()), 1000, 5000) == ()


def test_all_zero_data_still_lays_out() -> None:
    assert layout_waterfall(WaterfallData((Step("A", 0, 0, True, True),)), 1000, 5000)


@pytest.mark.parametrize(
    ("width", "height"), [(0, 5000), (-1, 5000), (1000, TOP_BAND + CATEGORY_BAND)]
)
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    data = WaterfallData((Step("A", 0, 1, True, True),))
    with pytest.raises(ValueError, match="too small"):
        layout_waterfall(data, width, height)


def test_falls_need_extra_room_below() -> None:
    rise = WaterfallData((Step("A", 0, 5, False, True),))
    fall = WaterfallData((Step("A", 0, -5, False, True),))
    height = TOP_BAND + CATEGORY_BAND + 100
    assert layout_waterfall(rise, 1000, height)
    with pytest.raises(ValueError, match="too small"):
        layout_waterfall(fall, 1000, height)


def test_layout_chart_picks_the_waterfall_layout() -> None:
    state = sample_waterfall_state()
    assert layout_chart(state, 24000, 12000) == layout_waterfall(
        parse_waterfall(state), 24000, 12000
    )


BRIDGE = WaterfallData(
    (
        Step("Start", 0, 100, True, True),
        Step("Up", 100, 130, False, True),
        Step("Down", 130, 120, False, True),
        Step("End", 0, 120, True, True),
    )
)


def bars(primitives: tuple) -> list[Rect]:
    return [p for p in primitives if isinstance(p, Rect) and p.series != BACKGROUND]


def test_bracket_arrow_measures_the_levels_and_meets_the_columns_above_their_labels() -> None:
    primitives = layout_waterfall(BRIDGE, 4000, 10000, (Annotation("difference", 0, 3),))
    start, end = bars(primitives)[0], bars(primitives)[3]
    line_y = LANE_HEIGHT - LANE_LINE_GAP
    assert primitives[-4:-1] == (
        Line(500, line_y, 500, start.y - LABEL_HEIGHT - LANE_LINE_GAP, "annotation"),
        Line(500, line_y, 3500, line_y, "annotation"),
        Line(3500, line_y, 3500, end.y - LABEL_HEIGHT - LANE_LINE_GAP, "annotation", arrow=True),
    )
    label = primitives[-1]
    assert isinstance(label, Text)
    assert label.text == "+20%"  # 100 -> 120


def test_arrow_to_a_falling_column_ends_on_its_top_not_above_its_label() -> None:
    primitives = layout_waterfall(BRIDGE, 4000, 10000, (Annotation("difference", 0, 2),))
    fall = bars(primitives)[2]
    head = next(p for p in primitives if isinstance(p, Line) and p.arrow)
    assert head.y2 == pytest.approx(fall.y - LANE_LINE_GAP)  # its label hangs below
    label = [p for p in primitives if isinstance(p, Text) and p.role == "annotation"]
    assert label[0].text == "+20%"  # the level after the fall is 120


def test_cagr_arrow_runs_over_the_levels() -> None:
    primitives = layout_waterfall(BRIDGE, 4000, 10000, (Annotation("cagr", 0, 3),))
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "annotation"]
    assert labels == ["CAGR +6.3%"]  # 100 -> 120 over three columns


def test_level_arrow_starts_at_the_connector_of_a_column() -> None:
    arrow = Annotation("difference", 0, 3, style="level")
    primitives = layout_waterfall(BRIDGE, 6000, 10000, (arrow,))
    plot_width = 6000 - LEVEL_LANE_WIDTH
    helpers = [p for p in primitives if isinstance(p, Line) and p.role == "helper"]
    connectors = [p for p in primitives if isinstance(p, Line) and p.role == "connector"]
    start = bars(primitives)[0]
    assert helpers[0].x1 == pytest.approx(start.x + start.width)
    assert helpers[0].y1 == pytest.approx(connectors[0].y1)  # the connector runs at level 100
    assert helpers[0].x2 == plot_width + LEVEL_ARROW_INSET
    head = next(p for p in primitives if isinstance(p, Line) and p.arrow)
    assert head.y1 > head.y2  # from level 100 up to level 120
    plain = layout_waterfall(BRIDGE, 6000, 10000)
    assert [r.y for r in bars(primitives)] == [r.y for r in bars(plain)]  # no lane above


def test_every_bracket_arrow_gets_its_own_lane_above_the_plot() -> None:
    arrows = (Annotation("difference", 0, 3), Annotation("cagr", 0, 3))
    primitives = layout_waterfall(BRIDGE, 4000, 10000, arrows)
    lines = {p.y1 for p in primitives if isinstance(p, Line) and p.role == "annotation"}
    assert {LANE_HEIGHT - LANE_LINE_GAP, 2 * LANE_HEIGHT - LANE_LINE_GAP} <= lines
    plain = bars(layout_waterfall(BRIDGE, 4000, 10000))
    assert all(r.height < p.height for r, p in zip(bars(primitives), plain, strict=True))


def test_arrows_pointing_past_the_data_are_not_drawn() -> None:
    stale = (Annotation("difference", 0, 9), Annotation("difference", 0, 1, series=2))
    assert layout_waterfall(BRIDGE, 4000, 10000, stale) == layout_waterfall(BRIDGE, 4000, 10000)


def test_structure_with_annotations_does_not_depend_on_size() -> None:
    arrows = (
        Annotation("difference", 0, 3),
        Annotation("cagr", 1, 3),
        Annotation("difference", 3, 0, style="level"),
        Annotation("axis_break", 0, 0),
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_waterfall(BRIDGE, width, height, arrows)
        ]

    assert shape(8000, 9000) == shape(30000, 20000) == shape(12000, 7000)


def test_lanes_leave_too_little_room_for_the_plot() -> None:
    level = Annotation("difference", 0, 3, style="level")
    with pytest.raises(ValueError, match="too small"):
        layout_waterfall(BRIDGE, LEVEL_LANE_WIDTH, 10000, (level,))


HIGH = WaterfallData(
    (
        Step("Start", 0, 1000, True, True),
        Step("Up", 1000, 1100, False, True),
        Step("Down", 1100, 1050, False, True),
        Step("End", 0, 1050, True, True),
    )
)
BREAK = (Annotation("axis_break", 0, 0),)


def test_axis_break_cuts_the_totals_and_moves_the_steps_down_as_a_whole() -> None:
    primitives = layout_waterfall(HIGH, 4000, 10000, BREAK)  # break 200..900, steps shown 300..400
    gaps = [p for p in primitives if isinstance(p, Rect) and p.series == BACKGROUND]
    start, up, down, end = bars(primitives)
    assert [g.x for g in gaps] == [start.x - BREAK_OVERHANG, end.x - BREAK_OVERHANG]
    assert gaps[0].height == BREAK_GAP
    assert start.height / up.height == pytest.approx(300 / 100)  # 1000 shows as 300
    assert up.y + up.height == pytest.approx(start.y)  # the step starts where the total ends
    assert down.y == pytest.approx(up.y)  # the fall starts at the level the rise ended
    assert down.height < up.height
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["1000", "+100", "-50", "1050"]  # real values


def test_a_manual_axis_break_is_drawn_and_one_beyond_the_steps_is_not() -> None:
    manual = (Annotation("axis_break", 0, 0, lower=100.0, upper=800.0),)
    gaps = [
        p
        for p in layout_waterfall(HIGH, 4000, 10000, manual)
        if isinstance(p, Rect) and p.series == BACKGROUND
    ]
    assert len(gaps) == 2
    too_high = (Annotation("axis_break", 0, 0, lower=100.0, upper=1200.0),)
    assert layout_waterfall(HIGH, 4000, 10000, too_high) == layout_waterfall(HIGH, 4000, 10000)


def test_arrows_meet_a_cut_total_where_it_ends() -> None:
    arrows = (*BREAK, Annotation("difference", 0, 3))
    primitives = layout_waterfall(HIGH, 4000, 10000, arrows)
    start = bars(primitives)[0]
    legs = [
        p for p in primitives if isinstance(p, Line) and p.role == "annotation" and p.x1 == p.x2
    ]
    leg = legs[0]  # the slanted lines of the break marks are not legs
    assert leg.y2 == pytest.approx(start.y - LABEL_HEIGHT - LANE_LINE_GAP)
    assert "+5%" in [p.text for p in primitives if isinstance(p, Text)]


def test_layout_chart_passes_the_annotations_to_the_waterfall_layout() -> None:
    state = replace(sample_waterfall_state(), annotations=(Annotation("difference", 0, 1),))
    assert layout_chart(state, 20000, 9000) == layout_waterfall(
        parse_waterfall(state), 20000, 9000, state.annotations
    )


def test_step_at_finds_the_column() -> None:
    # four slots of 1000; the label above and below a column belongs to it
    assert step_at(BRIDGE, 4000, (), 100, 5000) == (0, None)
    assert step_at(BRIDGE, 4000, (), 2999, 100) == (2, None)
    assert step_at(BRIDGE, 4000, (), 3000, 9500) == (3, None)  # its name


def test_step_at_misses_the_lanes_and_the_outside_of_the_box() -> None:
    bracket, level = Annotation("difference", 0, 3), Annotation("difference", 0, 3, style="level")
    assert step_at(BRIDGE, 4000, (), -1, 100) is None
    assert step_at(BRIDGE, 4000, (), 4000, 100) is None
    assert step_at(BRIDGE, 4000, (bracket,), 100, LANE_HEIGHT - 1) is None
    assert step_at(BRIDGE, 4000, (bracket,), 100, LANE_HEIGHT) == (0, None)
    assert step_at(BRIDGE, 6000, (level,), 100, 100) == (0, None)
    assert step_at(BRIDGE, 6000, (level,), 6000 - LEVEL_LANE_WIDTH, 100) is None
    assert step_at(WaterfallData(()), 4000, (), 100, 100) is None
