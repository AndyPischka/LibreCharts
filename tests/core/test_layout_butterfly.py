from dataclasses import replace

import pytest

from librecharts.core.datasheet import ChartData, Series, sample_butterfly_state
from librecharts.core.layout.butterfly import (
    CENTER_BAND,
    LABEL_WIDTH,
    OUTER_BAND,
    layout_butterfly,
    natural_length_per_unit,
)
from librecharts.core.layout.chart import layout_chart
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Primitive, Rect, Text

WIDTH, HEIGHT = 12000.0, 8000.0


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def bars(primitives: tuple[Primitive, ...], series: int) -> list[Rect]:
    return [
        p
        for p in primitives
        if isinstance(p, Rect) and p.series == series and p.height > 400 and p.width != 250
    ]


def test_the_first_series_grows_left_the_second_right_from_the_central_band() -> None:
    chart = data(("L", (10.0,)), ("R", (10.0,)), categories=("A",))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    (left,), (right,) = bars(primitives, 0), bars(primitives, 1)
    half = (WIDTH - CENTER_BAND) / 2 - OUTER_BAND
    assert left.x + left.width == pytest.approx(OUTER_BAND + half)
    assert right.x == pytest.approx(OUTER_BAND + half + CENTER_BAND)
    assert left.width == pytest.approx(right.width)


def test_both_halves_share_one_scale() -> None:
    chart = data(("L", (5.0, 10.0)), ("R", (20.0, 10.0)), categories=("A", "B"))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    left, right = bars(primitives, 0), bars(primitives, 1)
    # 5 on the left is a quarter of 20 on the right
    assert right[0].width / left[0].width == pytest.approx(4)
    assert left[1].width == pytest.approx(right[1].width)
    half = (WIDTH - CENTER_BAND) / 2 - OUTER_BAND
    assert right[0].width == pytest.approx(half)  # 20 is the axis maximum


def test_labels_sit_at_the_bar_ends_and_category_names_in_the_centre() -> None:
    chart = data(("L", (10.0,)), ("R", (20.0,)), categories=("A",))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    (left,), (right,) = bars(primitives, 0), bars(primitives, 1)
    values = {t.text: t for t in primitives if isinstance(t, Text) and t.role == "value"}
    assert values["10"].align == "right"
    assert values["10"].x + values["10"].width < left.x
    assert values["20"].align == "left"
    assert values["20"].x > right.x + right.width
    (name,) = [t for t in primitives if isinstance(t, Text) and t.role == "category"]
    assert (name.text, name.align, name.width) == ("A", "center", CENTER_BAND)
    assert name.x == pytest.approx(OUTER_BAND + (WIDTH - CENTER_BAND) / 2 - OUTER_BAND)


def test_labels_stay_inside_the_chart_box() -> None:
    chart = data(("L", (20.0,)), ("R", (20.0,)), categories=("A",))
    for p in layout_butterfly(chart, WIDTH, HEIGHT):
        if isinstance(p, Text):
            assert p.x >= -1e-6
            assert p.x + p.width <= WIDTH + 1e-6
    assert OUTER_BAND >= LABEL_WIDTH


def test_series_names_head_each_half_with_a_swatch() -> None:
    chart = data(("Men", (1.0,)), ("Women", (1.0,)), categories=("A",))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    names = [t for t in primitives if isinstance(t, Text) and t.role == "series"]
    assert [(t.text, t.align) for t in names] == [("Men", "right"), ("Women", "left")]
    assert names[0].x < names[1].x
    swatches = [p for p in primitives if isinstance(p, Rect) and p.width == p.height == 250]
    assert [s.series for s in swatches] == [0, 1]


def test_negative_and_empty_values_draw_no_bar_and_no_label() -> None:
    chart = data(("L", (-5.0, None, 3.0)), ("R", (None, 4.0, 0.0)), categories=("A", "B", "C"))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    assert len(bars(primitives, 0)) == 1
    assert len(bars(primitives, 1)) == 1
    assert sorted(t.text for t in primitives if isinstance(t, Text) and t.role == "value") == [
        "3",
        "4",
    ]


def test_further_series_are_ignored() -> None:
    chart = data(("L", (1.0,)), ("R", (2.0,)), ("X", (9.0,)), categories=("A",))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    assert not any(isinstance(p, Rect) and p.series == 2 for p in primitives)
    two = layout_butterfly(replace(chart, series=chart.series[:2]), WIDTH, HEIGHT)
    assert primitives == two  # the ignored series does not even move the scale


def test_a_chart_with_one_series_draws_only_the_left_half() -> None:
    chart = data(("L", (1.0, 2.0)), categories=("A", "B"))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT)
    assert len(bars(primitives, 0)) == 2
    assert not bars(primitives, 1)


def test_axis_and_gridlines_are_optional() -> None:
    chart = data(("L", (10.0,)), ("R", (20.0,)), categories=("A",))
    plain = layout_butterfly(chart, WIDTH, HEIGHT)
    axis = layout_butterfly(chart, WIDTH, HEIGHT, Format(axis=True))
    grid = layout_butterfly(chart, WIDTH, HEIGHT, Format(axis=True, gridlines=True))
    assert not [t for t in plain if isinstance(t, Text) and t.role == "axis"]
    ticks = [t.text for t in axis if isinstance(t, Text) and t.role == "axis"]
    assert ticks == ["0", "5", "10", "15", "20"] * 2  # both halves count up from the centre
    assert not any(isinstance(p, Line) and p.role == "grid" for p in axis)
    assert len([p for p in grid if isinstance(p, Line) and p.role == "grid"]) == 8


def test_a_given_length_per_unit_sets_the_scale() -> None:
    chart = data(("L", (10.0,)), ("R", (5.0,)), categories=("A",))
    primitives = layout_butterfly(chart, WIDTH, HEIGHT, length_per_unit=100.0)
    assert bars(primitives, 0)[0].width == pytest.approx(1000)
    assert bars(primitives, 1)[0].width == pytest.approx(500)


def test_the_natural_length_is_what_a_lone_chart_draws() -> None:
    chart = data(("L", (10.0,)), ("R", (20.0,)), categories=("A",))
    length = natural_length_per_unit(chart, WIDTH, HEIGHT)
    assert length is not None
    alone = layout_butterfly(chart, WIDTH, HEIGHT)
    shared = layout_butterfly(chart, WIDTH, HEIGHT, length_per_unit=length)
    assert alone == shared
    assert natural_length_per_unit(ChartData((), ()), WIDTH, HEIGHT) is None
    assert natural_length_per_unit(chart, 100, HEIGHT) is None


def test_sorting_orders_the_categories_by_the_left_series() -> None:
    state = replace(sample_butterfly_state(), sort="descending")
    names = [
        t.text
        for t in layout_chart(state, WIDTH, HEIGHT)
        if isinstance(t, Text) and t.role == "category"
    ]
    assert names == ["30-44", "45-59", "60+", "15-29", "0-14"]  # men: 9.4, 8.7, 8.2, 8.1, 6.5


def test_the_structure_does_not_depend_on_the_size() -> None:
    state = sample_butterfly_state()

    def kinds(width: float, height: float) -> list[str]:
        return [type(p).__name__ for p in layout_chart(state, width, height)]

    assert kinds(12000, 8000) == kinds(8000, 5000) == kinds(30000, 12000)


def test_an_empty_chart_has_no_primitives() -> None:
    assert layout_butterfly(ChartData((), ()), WIDTH, HEIGHT) == ()


def test_too_small_a_box_is_rejected() -> None:
    chart = data(("L", (1.0,)), categories=("A",))
    with pytest.raises(ValueError, match="too small"):
        layout_butterfly(chart, 3000, HEIGHT)
