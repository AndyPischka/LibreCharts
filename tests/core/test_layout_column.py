import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_state
from librecharts.core.layout.column import (
    CATEGORY_BAND,
    LABEL_HEIGHT,
    TOP_BAND,
    format_value,
    layout_column,
)
from librecharts.core.model import Grouping
from librecharts.core.primitives import Line, Rect, Text


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
