import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_state
from librecharts.core.layout.bar import (
    LABEL_GAP,
    LABEL_HEIGHT,
    LABEL_WIDTH,
    LEFT_BAND,
    RIGHT_BAND,
    layout_bar,
)
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.common import format_value
from librecharts.core.model import Grouping
from librecharts.core.primitives import Line, Rect, Text


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
