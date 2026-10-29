from dataclasses import replace

import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_state
from librecharts.core.layout.bar import (
    BRACKET_INSET,
    BRACKET_LABEL_GAP,
    BRACKET_LANE_WIDTH,
    LABEL_GAP,
    LABEL_HEIGHT,
    LABEL_WIDTH,
    LEFT_BAND,
    LEVEL_LANE_HEIGHT,
    RIGHT_BAND,
    bar_at,
    layout_bar,
)
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.column import BREAK_GAP, MIN_ARROW_LABEL_WIDTH
from librecharts.core.layout.common import format_value
from librecharts.core.model import Annotation, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Rect, Text


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def test_clustered_golden_geometry() -> None:
    # axis 0..20 maps to x 3000..7000; two slots of 2000 with bars 1400 thick
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    assert layout_bar(chart, "clustered", 8200, 4000) == (
        Line(3000, 0, 3000, 4000, "baseline"),
        Rect(3000, 300, 2000, 1400, 0),
        Text(5150, 700, 1050, LABEL_HEIGHT, "10", "left", "value"),
        Text(0, 0, 2850, 2000, "A", "right", "category"),
        Rect(3000, 2300, 4000, 1400, 0),
        Text(7150, 2700, 1050, LABEL_HEIGHT, "20", "left", "value"),
        Text(0, 2000, 2850, 2000, "B", "right", "category"),
    )


def test_stacked_golden_geometry() -> None:
    # one bar totalling 40 -> axis 0..40 maps to x 3000..7000; segments stack left to right
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    assert layout_bar(chart, "stacked", 8200, 2000) == (
        Line(3000, 0, 3000, 2000, "baseline"),
        Rect(3000, 300, 1000, 1400, 0),
        Text(3000, 300, 1000, 1400, "10", "center", "value"),
        Rect(4000, 300, 3000, 1400, 1),
        Text(4000, 300, 3000, 1400, "30", "center", "value"),
        Text(7150, 700, 1050, LABEL_HEIGHT, "40", "left", "total"),
        Text(0, 0, 2850, 2000, "X", "right", "category"),
    )


def test_stacked_negative_values_extend_to_the_left_of_the_baseline() -> None:
    chart = data(("A", (30.0,)), ("B", (-10.0,)), categories=("X",))
    primitives = layout_bar(chart, "stacked", 9400, 2000)
    baseline = next(p for p in primitives if isinstance(p, Line)).x1
    positive, negative = [p for p in primitives if isinstance(p, Rect)]
    assert positive.x == pytest.approx(baseline)
    assert negative.x + negative.width == pytest.approx(baseline)
    totals = [p for p in primitives if isinstance(p, Text) and p.role == "total"]
    assert [t.text for t in totals] == ["20"]


def test_single_segment_has_no_total_label() -> None:
    chart = data(("A", (5.0,)), ("B", (None,)), categories=("X",))
    texts = [p for p in layout_bar(chart, "stacked", 8200, 2000) if isinstance(p, Text)]
    assert {t.role for t in texts} == {"value", "category"}


def test_narrow_segments_get_an_empty_inside_label() -> None:
    chart = data(("A", (1.0,)), ("B", (1000.0,)), categories=("X",))
    values = [
        p.text
        for p in layout_bar(chart, "stacked", 8200, 2000)
        if isinstance(p, Text) and p.role == "value"
    ]
    assert values == ["", "1000"]


def test_clustered_negative_label_clears_the_category_names() -> None:
    chart = data(("A", (-10.0, 10.0)), categories=("X", "Y"))
    primitives = layout_bar(chart, "clustered", 9400, 4000)
    label = next(p for p in primitives if isinstance(p, Text) and p.text == "-10")
    category = next(p for p in primitives if isinstance(p, Text) and p.role == "category")
    assert label.align == "right"
    assert label.x >= category.x + category.width - 1e-9


def test_gaps_draw_nothing() -> None:
    chart = data(("A", (None, 4.0)), categories=("X", "Y"))
    for grouping in ("stacked", "clustered"):
        rects = [p for p in layout_bar(chart, grouping, 8200, 4000) if isinstance(p, Rect)]
        assert len(rects) == 1


def test_all_geometry_stays_inside_the_box() -> None:
    chart = parse(sample_state())
    for grouping in ("stacked", "clustered"):
        for p in layout_bar(chart, grouping, 24000, 12000):
            if isinstance(p, Rect | Text):
                assert p.x >= 0
                assert p.x + p.width <= 24000 + 1e-9
                assert p.y >= 0
                assert p.y + p.height <= 12000 + 1e-9


@pytest.mark.parametrize("grouping", ["stacked", "clustered"])
def test_structure_does_not_depend_on_size(grouping: Grouping) -> None:
    chart = data(("A", (1.0, -2.0, None)), ("B", (300.0, 5.0, 0.0)), categories=("X", "Y", "Z"))

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_bar(chart, grouping, width, height)
        ]

    assert shape(9000, 3000) == shape(30000, 20000) == shape(6000, 900)


def test_empty_data_yields_nothing() -> None:
    assert layout_bar(ChartData((), ()), "stacked", 8200, 3000) == ()


def test_all_zero_data_still_lays_out() -> None:
    chart = data(("A", (0.0, None)), categories=("X", "Y"))
    assert layout_bar(chart, "stacked", 8200, 3000)


@pytest.mark.parametrize(
    ("width", "height"),
    [(8200, 0), (8200, -1), (LEFT_BAND + RIGHT_BAND, 3000), (LEFT_BAND, 3000)],
)
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_bar(data(("A", (1.0,)), categories=("X",)), "stacked", width, height)


def test_negative_values_need_extra_room_on_the_left() -> None:
    positive = data(("A", (1.0,)), categories=("X",))
    negative = data(("A", (-1.0,)), categories=("X",))
    width = LEFT_BAND + RIGHT_BAND + 100
    assert layout_bar(positive, "clustered", width, 3000)
    with pytest.raises(ValueError, match="too small"):
        layout_bar(negative, "clustered", width, 3000)


def test_layout_chart_selects_the_layout_by_kind() -> None:
    from dataclasses import replace

    column = sample_state()
    bar = replace(column, kind="bar")
    assert layout_chart(column, 24000, 12000) != layout_chart(bar, 24000, 12000)
    assert layout_chart(bar, 24000, 12000) == layout_bar(parse(bar), "stacked", 24000, 12000)


def test_label_constants_are_consistent() -> None:
    assert LABEL_GAP < LABEL_WIDTH <= RIGHT_BAND
    assert format_value(2.5) == "2.5"


def test_bracket_arrow_golden_geometry() -> None:
    # one lane right of the plot: plot 3000..8600, axis 0..20; slots of 2000, bars 1400 thick
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_bar(chart, "clustered", 12000, 4000, (Annotation("difference", 0, 1),))
    lane_x = 3000 + 5600 + RIGHT_BAND + BRACKET_INSET
    assert primitives[-4:] == (
        Line(5800 + LABEL_WIDTH + 100, 1000, lane_x, 1000, "annotation"),
        Line(lane_x, 1000, lane_x, 3000, "annotation"),
        Line(lane_x, 3000, 8600 + LABEL_WIDTH + 100, 3000, "annotation", arrow=True),
        Text(
            lane_x + BRACKET_LABEL_GAP,
            (1000 + 3000 - LABEL_HEIGHT) / 2,
            BRACKET_LANE_WIDTH - BRACKET_INSET - BRACKET_LABEL_GAP,
            LABEL_HEIGHT,
            "+100%",
            "left",
            "annotation",
        ),
    )


def test_every_bracket_arrow_gets_its_own_lane_right_of_the_plot() -> None:
    chart = data(("S", (10.0, 20.0, 15.0)), categories=("A", "B", "C"))
    arrows = (Annotation("difference", 0, 1), Annotation("cagr", 0, 2))
    primitives = layout_bar(chart, "stacked", 16000, 6000, arrows)
    verticals = [
        p.x1 for p in primitives if isinstance(p, Line) and p.x1 == p.x2 and p.role == "annotation"
    ]
    assert verticals == [
        verticals[0],
        verticals[0] + BRACKET_LANE_WIDTH,
    ]
    plot_right = max(p.x + p.width for p in primitives if isinstance(p, Rect))
    assert plot_right <= 16000 - 2 * BRACKET_LANE_WIDTH - RIGHT_BAND + 1e-9


def test_bracket_arrow_head_is_on_the_end_bar() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_bar(chart, "stacked", 12000, 4000, (Annotation("difference", 1, 0),))
    head = next(p for p in primitives if isinstance(p, Line) and p.arrow)
    assert head.y2 == 1000  # bar A is the end
    assert head.x1 > head.x2  # drawn right to left, back onto the bar


def test_level_arrow_golden_geometry() -> None:
    # one level lane below a 4000 high plot; axis 0..20 maps to x 3000..7000
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1, style="level")
    primitives = layout_bar(chart, "stacked", 8200, 4000 + LEVEL_LANE_HEIGHT, (arrow,))
    assert primitives[0] == Line(3000, 0, 3000, 4000, "baseline")
    arrow_y = 4000 + 200
    assert primitives[-4:] == (
        Line(5000, 1700, 5000, arrow_y, "helper"),
        Line(7000, 3700, 7000, arrow_y, "helper"),
        Line(5000, arrow_y, 7000, arrow_y, "annotation", arrow=True),
        Text(5000, arrow_y + 100, 2000, LABEL_HEIGHT, "+100%", "center", "annotation"),
    )


def test_level_label_is_at_least_as_wide_as_the_minimum() -> None:
    chart = data(("S", (10.0, 11.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1, style="level")
    primitives = layout_bar(chart, "stacked", 8200, 5000, (arrow,))
    label = next(p for p in primitives if isinstance(p, Text) and p.role == "annotation")
    assert label.width == MIN_ARROW_LABEL_WIDTH


def test_level_arrow_of_a_clustered_bar_starts_at_its_bottom_edge() -> None:
    chart = data(("A", (10.0, 20.0)), ("B", (5.0, 8.0)), categories=("X", "Y"))
    arrow = Annotation("difference", 0, 1, series=0, style="level")
    primitives = layout_bar(chart, "clustered", 8200, 6000, (arrow,))
    helper = next(p for p in primitives if isinstance(p, Line) and p.role == "helper")
    bar = next(p for p in primitives if isinstance(p, Rect))  # series A in category X
    assert helper.x1 == pytest.approx(bar.x + bar.width)
    assert helper.y1 == pytest.approx(bar.y + bar.height)


def test_arrows_pointing_past_the_data_are_not_drawn() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    stale = (Annotation("difference", 0, 5), Annotation("difference", 0, 1, series=3))
    assert layout_bar(chart, "stacked", 12000, 4000, stale) == layout_bar(
        chart, "stacked", 12000, 4000
    )


@pytest.mark.parametrize("grouping", ["stacked", "clustered"])
def test_structure_with_annotations_does_not_depend_on_size(grouping: Grouping) -> None:
    chart = data(("A", (1.0, -2.0, None)), ("B", (300.0, 5.0, 0.0)), categories=("X", "Y", "Z"))
    arrows = (
        Annotation("difference", 0, 2),
        Annotation("cagr", 2, 1, series=1),
        Annotation("difference", 1, 0, style="level"),
        Annotation("axis_break", 0, 0),
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_bar(chart, grouping, width, height, arrows)
        ]

    assert shape(16000, 7000) == shape(40000, 20000) == shape(20000, 9000)


def test_lanes_leave_too_little_room_for_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    with pytest.raises(ValueError, match="too small"):
        layout_bar(chart, "stacked", 6000, 4000, (Annotation("difference", 0, 1),))
    with pytest.raises(ValueError, match="too small"):
        layout_bar(
            chart,
            "stacked",
            8200,
            LEVEL_LANE_HEIGHT,
            (Annotation("difference", 0, 1, style="level"),),
        )


BREAK = (Annotation("axis_break", 0, 0),)
TALL = data(("S", (10.0, 100.0, 20.0)), categories=("A", "B", "C"))


def test_axis_break_marks_the_bar_beyond_it_with_a_vertical_gap() -> None:
    primitives = layout_bar(TALL, "stacked", 10000, 6000, BREAK)  # break 22..96, 100 shows as 26
    gaps = [p for p in primitives if isinstance(p, Rect) and p.series == BACKGROUND]
    bars = [p for p in primitives if isinstance(p, Rect) and p.series != BACKGROUND]
    assert len(gaps) == 1
    assert gaps[0].width == BREAK_GAP
    assert gaps[0].y < bars[1].y
    assert gaps[0].y + gaps[0].height > bars[1].y + bars[1].height
    assert bars[2].width < bars[1].width  # C (20) stays shorter than the cut bar
    assert bars[1].x + bars[1].width > gaps[0].x + gaps[0].width


def test_axis_break_marks_every_bar_beyond_it_in_a_clustered_chart() -> None:
    chart = data(("A", (10.0, 100.0)), ("B", (12.0, 11.0)), categories=("X", "Y"))
    primitives = layout_bar(chart, "clustered", 10000, 6000, BREAK)
    gaps = [p for p in primitives if isinstance(p, Rect) and p.series == BACKGROUND]
    bars = [p for p in primitives if isinstance(p, Rect) and p.series != BACKGROUND]
    assert len(gaps) == 1
    assert gaps[0].y == bars[2].y  # on the cut bar (A in Y), not reaching beyond it
    assert gaps[0].height == bars[2].height


def test_arrows_meet_the_cut_bar_where_it_ends() -> None:
    arrows = (*BREAK, Annotation("difference", 0, 1), Annotation("difference", 0, 1, style="level"))
    primitives = layout_bar(TALL, "stacked", 16000, 8000, arrows)
    bar_b = [p for p in primitives if isinstance(p, Rect) and p.series != BACKGROUND][1]
    head = next(
        p for p in primitives if isinstance(p, Line) and p.arrow and p.y1 == p.y2 and p.x2 < p.x1
    )
    assert head.x2 == pytest.approx(bar_b.x + bar_b.width + LABEL_WIDTH + 100)
    helper = [p for p in primitives if isinstance(p, Line) and p.role == "helper"][1]
    assert helper.x1 == pytest.approx(bar_b.x + bar_b.width)
    assert "+900%" in [p.text for p in primitives if isinstance(p, Text)]


def test_layout_chart_passes_the_annotations_to_the_bar_layout() -> None:
    state = replace(sample_state(), kind="bar", annotations=(Annotation("difference", 0, 1),))
    assert layout_chart(state, 20000, 9000) == layout_bar(
        parse(state), state.grouping, 20000, 9000, state.annotations
    )


def test_100_percent_bars_are_full_and_show_their_shares() -> None:
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    primitives = layout_bar(chart, "stacked", 8200, 2000, percent=True)
    rects_ = [p for p in primitives if isinstance(p, Rect)]
    assert len(rects_) == 2
    assert sum(r.width for r in rects_) == pytest.approx(4000)
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["25%", "75%"]
    total = next(p for p in primitives if isinstance(p, Text) and p.role == "total")
    assert total.text == "40"
    assert total.x == pytest.approx(7000 + LABEL_GAP)


def test_100_percent_bars_ignore_negatives_and_draw_no_annotations() -> None:
    chart = data(("A", (10.0,)), ("B", (-5.0,)), categories=("X",))
    arrows = (Annotation("difference", 0, 1),)
    assert layout_bar(chart, "stacked", 8200, 2000, arrows, percent=True) == layout_bar(
        chart, "stacked", 8200, 2000, percent=True
    )
    assert [
        p.text
        for p in layout_bar(chart, "stacked", 8200, 2000, percent=True)
        if isinstance(p, Text) and p.role == "value"
    ] == ["100%"]


def test_an_empty_100_percent_bar_draws_nothing() -> None:
    chart = data(("A", (None,)), categories=("X",))
    primitives = layout_bar(chart, "stacked", 8200, 2000, percent=True)
    assert not any(isinstance(p, Rect) for p in primitives)


def test_layout_chart_sorts_the_categories() -> None:
    state = replace(sample_state(), sort="descending")
    categories = [
        p.text
        for p in layout_chart(state, 24000, 12000)
        if isinstance(p, Text) and p.role == "category"
    ]
    assert categories == ["2025", "2024", "2023"]  # column sums 45, 42, 35


def test_layout_chart_moves_annotations_with_their_category() -> None:
    state = replace(
        sample_state(), sort="descending", annotations=(Annotation("difference", 0, 2),)
    )
    label = next(
        p
        for p in layout_chart(state, 24000, 12000)
        if isinstance(p, Text) and p.role == "annotation"
    )
    # 2023 -> 2025 becomes the arrow from the last to the first display column
    assert label.text == "+28.6%"


def test_bar_at_finds_the_category_and_the_series() -> None:
    chart = data(("A", (10.0, 20.0)), ("B", (5.0, 8.0)), categories=("X", "Y"))
    # plot 3000..9000, slots of 2000, bars 1400 thick from 300, 700 each
    assert bar_at(chart, "clustered", 12000, 4000, (), 4000, 400) == (0, 0)
    assert bar_at(chart, "clustered", 12000, 4000, (), 4000, 1000) == (0, 1)
    assert bar_at(chart, "clustered", 12000, 4000, (), 4000, 2400) == (1, 0)
    assert bar_at(chart, "clustered", 12000, 4000, (), 4000, 150) == (0, None)  # between bars
    assert bar_at(chart, "stacked", 12000, 4000, (), 4000, 150) == (0, None)
    assert bar_at(chart, "stacked", 12000, 4000, (), 100, 3900) == (1, None)  # on the name


def test_bar_at_misses_the_lanes_and_the_outside_of_the_box() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    bracket, level = Annotation("difference", 0, 1), Annotation("difference", 0, 1, style="level")
    assert bar_at(chart, "stacked", 12000, 4000, (), -1, 1000) is None
    assert bar_at(chart, "stacked", 12000, 4000, (), 4000, -1) is None
    assert bar_at(chart, "stacked", 12000, 4000, (), 4000, 4000) is None
    # the bracket lane starts after the plot and the label band: 3000 + 5600 + 1200
    assert bar_at(chart, "stacked", 12000, 4000, (bracket,), 9799, 1000) == (0, None)
    assert bar_at(chart, "stacked", 12000, 4000, (bracket,), 9800, 1000) is None
    below = 4000 - LEVEL_LANE_HEIGHT
    assert bar_at(chart, "stacked", 8200, 4000, (level,), 4000, below - 1) == (1, None)
    assert bar_at(chart, "stacked", 8200, 4000, (level,), 4000, below) is None


def test_bar_at_nothing_to_hit_without_data_or_room() -> None:
    empty = ChartData((), ())
    assert bar_at(empty, "stacked", 12000, 4000, (), 4000, 1000) is None
    chart = data(("S", (10.0,)), categories=("A",))
    assert bar_at(chart, "stacked", 3000, 4000, (), 100, 1000) is None
