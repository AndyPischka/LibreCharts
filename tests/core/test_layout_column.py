import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_state
from librecharts.core.layout.column import (
    BREAK_GAP,
    BREAK_OVERHANG,
    BREAK_SLANT,
    CATEGORY_BAND,
    LABEL_HEIGHT,
    LANE_HEIGHT,
    LANE_LINE_GAP,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    MIN_ARROW_LABEL_WIDTH,
    TOP_BAND,
    format_value,
    layout_column,
)
from librecharts.core.model import Annotation, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def test_clustered_golden_geometry() -> None:
    # axis 0..20, plot from y=800 to y=9000 (height 10000), two slots of 1000, bars 700 wide
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    assert layout_column(chart, "clustered", 2000, 10000) == (
        Line(0, 9000, 2000, 9000, "baseline"),
        Rect(150, 4900, 700, 4100, 0),
        Text(150, 4300, 700, LABEL_HEIGHT, "10", "center", "value"),
        Text(0, 9000, 1000, CATEGORY_BAND, "A", "center", "category"),
        Rect(1150, 800, 700, 8200, 0),
        Text(1150, 200, 700, LABEL_HEIGHT, "20", "center", "value"),
        Text(1000, 9000, 1000, CATEGORY_BAND, "B", "center", "category"),
    )


def test_stacked_golden_geometry() -> None:
    # one column totalling 40 -> axis 0..40; segments stack bottom-up in series order
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    assert layout_column(chart, "stacked", 1000, 10000) == (
        Line(0, 9000, 1000, 9000, "baseline"),
        Rect(150, 6950, 700, 2050, 0),
        Text(150, 6950, 700, 2050, "10", "center", "value"),
        Rect(150, 800, 700, 6150, 1),
        Text(150, 800, 700, 6150, "30", "center", "value"),
        Text(150, 200, 700, LABEL_HEIGHT, "40", "center", "total"),
        Text(0, 9000, 1000, CATEGORY_BAND, "X", "center", "category"),
    )


def test_stacked_negative_values_hang_below_the_baseline() -> None:
    chart = data(("A", (30.0,)), ("B", (-10.0,)), categories=("X",))
    rects = [p for p in layout_column(chart, "stacked", 1000, 10000) if isinstance(p, Rect)]
    baseline = next(
        p for p in layout_column(chart, "stacked", 1000, 10000) if isinstance(p, Line)
    ).y1
    positive, negative = rects
    assert positive.y + positive.height == pytest.approx(baseline)
    assert negative.y == pytest.approx(baseline)


def test_total_is_the_net_sum() -> None:
    chart = data(("A", (30.0,)), ("B", (-10.0,)), categories=("X",))
    totals = [
        p
        for p in layout_column(chart, "stacked", 1000, 10000)
        if isinstance(p, Text) and p.role == "total"
    ]
    assert [t.text for t in totals] == ["20"]


def test_single_segment_has_no_total_label() -> None:
    chart = data(("A", (5.0,)), ("B", (None,)), categories=("X",))
    texts = [p for p in layout_column(chart, "stacked", 1000, 10000) if isinstance(p, Text)]
    assert {t.role for t in texts} == {"value", "category"}


def test_flat_segments_get_an_empty_inside_label() -> None:
    chart = data(("A", (1.0,)), ("B", (1000.0,)), categories=("X",))
    values = [
        p.text
        for p in layout_column(chart, "stacked", 1000, 10000)
        if isinstance(p, Text) and p.role == "value"
    ]
    assert values == ["", "1000"]


@pytest.mark.parametrize("grouping", ["stacked", "clustered"])
def test_structure_does_not_depend_on_size(grouping: Grouping) -> None:
    chart = data(("A", (1.0, -2.0, None)), ("B", (300.0, 5.0, 0.0)), categories=("X", "Y", "Z"))

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_column(chart, grouping, width, height)
        ]

    assert shape(3000, 4000) == shape(30000, 20000) == shape(9000, 2500)


def test_gaps_and_zeros_draw_nothing() -> None:
    chart = data(("A", (None, 0.0, 4.0)), categories=("X", "Y", "Z"))
    for grouping in ("stacked", "clustered"):
        rects = [p for p in layout_column(chart, grouping, 3000, 10000) if isinstance(p, Rect)]
        assert len(rects) == (1 if grouping == "stacked" else 2)  # clustered draws the 0 bar


def test_clustered_negative_label_hangs_below_the_bar_and_clears_the_categories() -> None:
    chart = data(("A", (-10.0, 10.0)), categories=("X", "Y"))
    primitives = layout_column(chart, "clustered", 2000, 10000)
    label = next(p for p in primitives if isinstance(p, Text) and p.text == "-10")
    category = next(p for p in primitives if isinstance(p, Text) and p.role == "category")
    assert label.y + label.height <= category.y + 1e-9


def test_all_geometry_stays_inside_the_box() -> None:
    chart = parse(sample_state())
    for grouping in ("stacked", "clustered"):
        for p in layout_column(chart, grouping, 24000, 12000):
            if isinstance(p, Rect | Text):
                assert p.x >= 0
                assert p.x + p.width <= 24000 + 1e-9
                assert p.y >= 0
                assert p.y + p.height <= 12000 + 1e-9


def test_layout_is_deterministic() -> None:
    chart = parse(sample_state())
    assert layout_column(chart, "stacked", 24000, 12000) == layout_column(
        chart, "stacked", 24000, 12000
    )


def test_empty_data_yields_nothing() -> None:
    assert layout_column(ChartData((), ()), "stacked", 1000, 5000) == ()


def test_all_zero_data_still_lays_out() -> None:
    chart = data(("A", (0.0, None)), categories=("X", "Y"))
    assert layout_column(chart, "stacked", 2000, 5000)  # axis fallback, no division by zero


@pytest.mark.parametrize(
    ("width", "height"), [(0, 5000), (-1, 5000), (1000, TOP_BAND + CATEGORY_BAND)]
)
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_column(data(("A", (1.0,)), categories=("X",)), "stacked", width, height)


@pytest.mark.parametrize(
    ("value", "text"),
    [(10.0, "10"), (-3.0, "-3"), (2.5, "2.5"), (1.005, "1"), (0.1 + 0.2, "0.3"), (0.001, "0")],
)
def test_format_value(value: float, text: str) -> None:
    assert format_value(value) == text


def test_difference_arrow_golden_geometry() -> None:
    # one lane: the plot starts at 800 + 800; axis 0..20 over 7400 -> 10 is at 5300
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1)
    primitives = layout_column(chart, "clustered", 2000, 10000, (arrow,))
    assert primitives[-4:] == (
        Line(500, 700, 500, 5300 - LABEL_HEIGHT - LANE_LINE_GAP, "annotation"),
        Line(500, 700, 1500, 700, "annotation"),
        Line(1500, 700, 1500, 1600 - LABEL_HEIGHT - LANE_LINE_GAP, "annotation", arrow=True),
        Text(100, 100, MIN_ARROW_LABEL_WIDTH, LABEL_HEIGHT, "+100%", "center", "annotation"),
    )


def test_every_arrow_gets_its_own_lane_above_the_plot() -> None:
    chart = data(("S", (10.0, 20.0, 15.0)), categories=("A", "B", "C"))
    arrows = (Annotation("difference", 0, 1), Annotation("cagr", 0, 2))
    primitives = layout_column(chart, "stacked", 3000, 10000, arrows)
    lines = [p.y1 for p in primitives if isinstance(p, Line) and p.role == "annotation"]
    assert sorted(set(lines)) == [LANE_HEIGHT - LANE_LINE_GAP, 2 * LANE_HEIGHT - LANE_LINE_GAP]
    tallest = min(p.y for p in primitives if isinstance(p, Rect))
    assert tallest == 2 * LANE_HEIGHT + TOP_BAND


def test_arrow_runs_right_to_left_with_the_head_on_the_end_column() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_column(chart, "stacked", 2000, 10000, (Annotation("difference", 1, 0),))
    legs = [p for p in primitives if isinstance(p, Line) and p.role == "annotation"]
    head = next(p for p in legs if p.arrow)
    assert head.x1 == head.x2 == 500  # column A
    assert legs[1].x1 < legs[1].x2  # lines always run left to right


def test_clustered_arrow_meets_the_picked_bar() -> None:
    chart = data(("A", (10.0, 20.0)), ("B", (5.0, 8.0)), categories=("X", "Y"))
    primitives = layout_column(
        chart, "clustered", 2000, 10000, (Annotation("difference", 0, 1, series=1),)
    )
    head = next(p for p in primitives if isinstance(p, Line) and p.arrow)
    bar = [p for p in primitives if isinstance(p, Rect)][3]  # series B in category Y
    assert head.x1 == pytest.approx(bar.x + bar.width / 2)
    assert head.y2 < bar.y - LABEL_HEIGHT


def test_arrows_pointing_past_the_data_are_not_drawn() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    stale = (Annotation("difference", 0, 5), Annotation("difference", 0, 1, series=3))
    assert layout_column(chart, "stacked", 2000, 10000, stale) == layout_column(
        chart, "stacked", 2000, 10000
    )


@pytest.mark.parametrize("grouping", ["stacked", "clustered"])
def test_structure_with_arrows_does_not_depend_on_size(grouping: Grouping) -> None:
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
            for p in layout_column(chart, grouping, width, height, arrows)
        ]

    assert shape(3000, 6000) == shape(30000, 20000) == shape(9000, 4500)


def test_arrow_geometry_stays_inside_the_box() -> None:
    chart = parse(sample_state())
    arrows = (Annotation("difference", 0, 2), Annotation("difference", 2, 1))
    for p in layout_column(chart, "stacked", 24000, 12000, arrows):
        if isinstance(p, Rect | Text):
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9
        else:
            assert min(p.y1, p.y2) >= 0
            assert max(p.y1, p.y2) <= 12000


def test_level_arrow_golden_geometry() -> None:
    # one level lane takes 2000 of the 4000 wide box; plot 800..9000, axis 0..20
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1, style="level")
    primitives = layout_column(chart, "stacked", 4000, 10000, (arrow,))
    assert primitives[0] == Line(0, 9000, 2000, 9000, "baseline")
    arrow_x = 2000 + LEVEL_ARROW_INSET
    assert primitives[-4:] == (
        Line(850, 4900, arrow_x, 4900, "helper"),
        Line(1850, 800, arrow_x, 800, "helper"),
        Line(arrow_x, 4900, arrow_x, 800, "annotation", arrow=True),
        Text(
            arrow_x + LEVEL_LABEL_GAP,
            (4900 + 800 - LABEL_HEIGHT) / 2,
            LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
            LABEL_HEIGHT,
            "+100%",
            "left",
            "annotation",
        ),
    )


def test_level_arrows_get_lanes_right_of_the_plot_and_no_lane_above() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    levels = (
        Annotation("difference", 0, 1, style="level"),
        Annotation("difference", 1, 0, style="level", label="absolute"),
    )
    primitives = layout_column(chart, "stacked", 6000, 10000, levels)
    heads = [p.x1 for p in primitives if isinstance(p, Line) and p.arrow]
    assert heads == [2000 + LEVEL_ARROW_INSET, 2000 + LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET]
    assert min(p.y for p in primitives if isinstance(p, Rect)) == TOP_BAND


def test_level_arrow_of_a_clustered_bar_starts_at_its_right_edge() -> None:
    chart = data(("A", (10.0, 20.0)), ("B", (5.0, 8.0)), categories=("X", "Y"))
    arrow = Annotation("difference", 0, 1, series=0, style="level")
    primitives = layout_column(chart, "clustered", 4000, 10000, (arrow,))
    helper = next(p for p in primitives if isinstance(p, Line) and p.role == "helper")
    bar = next(p for p in primitives if isinstance(p, Rect))  # series A in category X
    assert helper.x1 == pytest.approx(bar.x + bar.width)
    assert helper.y1 == pytest.approx(bar.y)


def test_level_lanes_leave_too_little_room_for_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    with pytest.raises(ValueError, match="too small"):
        layout_column(
            chart,
            "stacked",
            LEVEL_LANE_WIDTH,
            10000,
            (Annotation("difference", 0, 1, style="level"),),
        )


TALL = data(("S", (10.0, 100.0, 20.0)), categories=("A", "B", "C"))
BREAK = (Annotation("axis_break", 0, 0),)  # automatic
# automatic: second tallest column 20 -> break from 22 to 96, B (100) continues up to 26;
# the axis then runs 0..30 over 8200 from 800


def y_of(value: float) -> float:
    return 800 + (30 - value) / 30 * 8200


def rects(primitives: tuple[Primitive, ...], *, gaps: bool = False) -> list[Rect]:
    return [p for p in primitives if isinstance(p, Rect) and (p.series == BACKGROUND) == gaps]


def test_automatic_axis_break_golden_geometry() -> None:
    primitives = layout_column(TALL, "stacked", 3000, 10000, BREAK)
    column_a, column_b, column_c = rects(primitives)
    assert column_b.y == pytest.approx(y_of(26))
    assert column_c.y == pytest.approx(y_of(20))  # the second tallest column is not cut
    assert column_a.y == pytest.approx(y_of(10))
    label = next(p for p in primitives if isinstance(p, Text) and p.text == "100")
    assert label.y == pytest.approx(column_b.y)  # inside label keeps the real value
    gap_top = y_of(22) - BREAK_GAP / 2
    left, right = 1150 - BREAK_OVERHANG, 1850 + BREAK_OVERHANG
    assert primitives[primitives.index(label) + 1 : primitives.index(label) + 4] == (
        Rect(left, gap_top, right - left, BREAK_GAP, BACKGROUND),
        Line(left, gap_top, right, gap_top + BREAK_SLANT, "annotation"),
        Line(left, gap_top + BREAK_GAP - BREAK_SLANT, right, gap_top + BREAK_GAP, "annotation"),
    )


def test_axis_break_scales_the_other_columns_up() -> None:
    plain = rects(layout_column(TALL, "stacked", 3000, 10000))[0].height
    assert rects(layout_column(TALL, "stacked", 3000, 10000, BREAK))[0].height > 3 * plain


@pytest.mark.parametrize(
    "chart",
    [
        data(("S", (10.0, 25.0, 20.0)), categories=("A", "B", "C")),  # nobody dwarfs the others
        data(("S", (10.0,)), categories=("A",)),  # only one column
        data(("S", (0.0, 50.0)), categories=("A", "B")),  # the rest is empty
    ],
)
def test_automatic_axis_break_without_a_dwarfing_column_changes_nothing(chart: ChartData) -> None:
    assert layout_column(chart, "stacked", 3000, 10000, BREAK) == layout_column(
        chart, "stacked", 3000, 10000
    )


def test_manual_axis_break_applies_to_every_column_reaching_beyond_it() -> None:
    chart = data(("S", (10.0, 100.0, 90.0)), categories=("A", "B", "C"))
    manual = (Annotation("axis_break", 0, 0, lower=30.0, upper=60.0),)
    primitives = layout_column(chart, "stacked", 3000, 10000, manual)
    # B ends at 100 - 30 = 70, C at 60; the axis runs 0..80
    column_a, column_b, column_c = rects(primitives)
    assert column_b.y == pytest.approx(800 + (80 - 70) / 80 * 8200)
    assert column_c.y == pytest.approx(800 + (80 - 60) / 80 * 8200)
    assert column_a.height == pytest.approx(10 / 80 * 8200)
    assert len(rects(primitives, gaps=True)) == 2  # one mark per cut column, none on A


def test_manual_axis_break_leaves_columns_inside_the_removed_range_at_the_break() -> None:
    chart = data(("S", (10.0, 100.0, 45.0)), categories=("A", "B", "C"))
    manual = (Annotation("axis_break", 0, 0, lower=30.0, upper=60.0),)
    column_c = rects(layout_column(chart, "stacked", 3000, 10000, manual))[2]
    assert column_c.height == pytest.approx(30 / 80 * 8200)  # axis 0..80, C drawn up to 30


def test_manual_axis_break_above_every_column_draws_nothing() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    manual = (Annotation("axis_break", 0, 0, lower=30.0, upper=60.0),)
    assert layout_column(chart, "stacked", 2000, 10000, manual) == layout_column(
        chart, "stacked", 2000, 10000
    )


def test_the_last_axis_break_wins() -> None:
    chart = data(("S", (10.0, 100.0, 90.0)), categories=("A", "B", "C"))
    first = Annotation("axis_break", 0, 0, lower=30.0, upper=60.0)
    last = Annotation("axis_break", 0, 0, lower=20.0, upper=40.0)
    assert layout_column(chart, "stacked", 3000, 10000, (first, last)) == layout_column(
        chart, "stacked", 3000, 10000, (last,)
    )


def test_axis_break_marks_every_bar_beyond_it_in_a_clustered_chart() -> None:
    chart = data(("A", (10.0, 100.0)), ("B", (12.0, 11.0)), categories=("X", "Y"))
    primitives = layout_column(chart, "clustered", 2000, 10000, BREAK)  # break 13.2..96.8
    gaps, bars = rects(primitives, gaps=True), rects(primitives)
    assert len(gaps) == 1
    assert gaps[0].x == bars[2].x  # on the cut bar (A in Y), not reaching beyond it
    assert gaps[0].width == bars[2].width
    assert bars[3].y > bars[2].y  # B in Y stays below the cut bar


def test_arrows_meet_the_cut_column_where_it_ends() -> None:
    arrows = (*BREAK, Annotation("difference", 0, 1), Annotation("difference", 0, 1, style="level"))
    primitives = layout_column(TALL, "stacked", 5000, 10000, arrows)
    column_b = rects(primitives)[1]
    head = next(
        p for p in primitives if isinstance(p, Line) and p.arrow and p.x1 == p.x2 and p.y2 > p.y1
    )
    assert head.y2 == pytest.approx(column_b.y - LABEL_HEIGHT - LANE_LINE_GAP)
    helper = [p for p in primitives if isinstance(p, Line) and p.role == "helper"][1]
    assert helper.y1 == pytest.approx(column_b.y)
    assert "+900%" in [p.text for p in primitives if isinstance(p, Text)]


def test_100_percent_columns_are_full_and_show_their_shares() -> None:
    # one column totalling 40: axis 0..100 over 8200 from 800
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    primitives = layout_column(chart, "stacked", 1000, 10000, percent=True)
    rects_ = [p for p in primitives if isinstance(p, Rect)]
    assert len(rects_) == 2
    assert rects_[0].height == pytest.approx(25 / 100 * 8200)
    assert rects_[1].height == pytest.approx(75 / 100 * 8200)
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["25%", "75%"]
    total = next(p for p in primitives if isinstance(p, Text) and p.role == "total")
    assert total.text == "40"
    assert total.y == pytest.approx(800 - LABEL_HEIGHT)


def test_100_percent_charts_ignore_negative_values() -> None:
    chart = data(("A", (10.0,)), ("B", (-5.0,)), categories=("X",))
    primitives = layout_column(chart, "stacked", 1000, 10000, percent=True)
    assert len([p for p in primitives if isinstance(p, Rect)]) == 1
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["100%"]
    total = next(p for p in primitives if isinstance(p, Text) and p.role == "total")
    assert total.text == "10"


def test_100_percent_charts_draw_no_annotations() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrows = (Annotation("difference", 0, 1), Annotation("axis_break", 0, 0))
    assert layout_column(chart, "stacked", 2000, 10000, arrows, percent=True) == layout_column(
        chart, "stacked", 2000, 10000, percent=True
    )


def test_100_percent_structure_does_not_depend_on_size() -> None:
    chart = data(("A", (1.0, -2.0, None)), ("B", (300.0, 5.0, 0.0)), categories=("X", "Y", "Z"))

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_column(chart, "stacked", width, height, percent=True)
        ]

    assert shape(3000, 4000) == shape(30000, 20000) == shape(9000, 2500)
