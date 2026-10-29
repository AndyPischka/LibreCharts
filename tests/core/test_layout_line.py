import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_line_state
from librecharts.core.layout.common import MIN_ARROW_LABEL_WIDTH
from librecharts.core.layout.line import (
    CATEGORY_BAND,
    LABEL_GAP,
    LABEL_HEIGHT,
    LANE_HEIGHT,
    LANE_LINE_GAP,
    LEVEL_ARROW_INSET,
    SERIES_BAND,
    SERIES_LABEL_GAP,
    TOP_BAND,
    layout_line,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import Line, Marker, Polyline, Primitive, Rect, Text

LABELS = Format(series_names="labels")


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def test_line_golden_geometry() -> None:
    # axis 0..20 over 8200 from y=800, two slots of 1000, points at the slot centres
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    assert layout_line(chart, 2000, 10000) == (
        Line(0, 9000, 2000, 9000, "baseline"),
        Text(0, 9000, 1000, CATEGORY_BAND, "A", "center", "category"),
        Text(1000, 9000, 1000, CATEGORY_BAND, "B", "center", "category"),
        Polyline(((500, 4900), (1500, 800)), 0),
        Marker(500, 4900, 0),
        Marker(1500, 800, 0),
        Text(0, 4900 - LABEL_HEIGHT - LABEL_GAP, 1000, LABEL_HEIGHT, "10", "center", "value"),
        Text(1000, 800 - LABEL_HEIGHT - LABEL_GAP, 1000, LABEL_HEIGHT, "20", "center", "value"),
    )


def test_a_gap_splits_the_line_and_drops_its_marker_and_label() -> None:
    chart = data(("S", (1.0, None, 3.0, 4.0)), categories=("A", "B", "C", "D"))
    primitives = layout_line(chart, 4000, 10000)
    lines = [p for p in primitives if isinstance(p, Polyline)]
    assert [len(p.points) for p in lines] == [1, 2]
    assert len([p for p in primitives if isinstance(p, Marker)]) == 3
    assert [p.text for p in primitives if isinstance(p, Text) and p.role == "value"] == [
        "1",
        "3",
        "4",
    ]


def test_markers_can_be_switched_off() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_line(chart, 2000, 10000, fmt=Format(markers=False))
    assert not any(isinstance(p, Marker) for p in primitives)
    assert any(isinstance(p, Polyline) for p in primitives)


def test_negative_values_label_below_the_point() -> None:
    chart = data(("S", (-5.0,)), categories=("A",))
    label = next(
        p for p in layout_line(chart, 1000, 10000) if isinstance(p, Text) and p.text == "-5"
    )
    point = next(p for p in layout_line(chart, 1000, 10000) if isinstance(p, Marker))
    assert label.y > point.y


def test_series_names_sit_right_of_the_last_point() -> None:
    chart = data(("Revenue", (10.0, 20.0)), ("Costs", (5.0, 8.0)), categories=("A", "B"))
    primitives = layout_line(chart, 6000, 10000, fmt=LABELS)
    names = [p for p in primitives if isinstance(p, Text) and p.role == "series"]
    assert names[0].text == "Costs"  # names run bottom-up so that the spread never overlaps
    assert names[1].text == "Revenue"
    assert names[0].y > names[1].y
    # the plot shrinks by the series band, so the names start right of it
    assert all(p.x == 6000 - SERIES_BAND + SERIES_LABEL_GAP for p in names)
    assert names[0].y > names[1].y  # Revenue is the higher point, drawn first
    assert names[0].width == SERIES_BAND - SERIES_LABEL_GAP


def test_series_names_make_room_for_overlapping_points() -> None:
    chart = data(("A", (10.0,)), ("B", (10.0,)), categories=("X",))
    names = [
        p
        for p in layout_line(chart, 6000, 10000, fmt=LABELS)
        if isinstance(p, Text) and p.role == "series"
    ]
    assert abs(names[0].y - names[1].y) == pytest.approx(LABEL_HEIGHT)


def test_a_legend_sits_above_the_plot() -> None:
    chart = data(("A", (10.0,)), ("B", (20.0,)), categories=("X",))
    primitives = layout_line(chart, 2000, 10000, fmt=Format(series_names="legend"))
    assert [p.text for p in primitives if isinstance(p, Text) and p.role == "series"] == ["A", "B"]
    first = primitives[0]
    assert isinstance(first, Rect)
    assert first.y < TOP_BAND


def test_the_value_axis_and_gridlines_are_optional() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    plain = layout_line(chart, 2000, 10000)
    with_axis = layout_line(chart, 2000, 10000, fmt=Format(axis=True))
    with_grid = layout_line(chart, 2000, 10000, fmt=Format(axis=True, gridlines=True))
    assert not any(isinstance(p, Line) and p.role == "axis" for p in plain)
    assert any(isinstance(p, Line) and p.role == "axis" for p in with_axis)
    assert not any(isinstance(p, Line) and p.role == "grid" for p in with_axis)
    assert len([p for p in with_grid if isinstance(p, Line) and p.role == "grid"]) == 4


def test_a_break_arrow_lands_on_the_points() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1)
    primitives = layout_line(chart, 2000, 10000, (arrow,))
    head = next(p for p in primitives if isinstance(p, Line) and p.arrow)
    assert head.x1 == head.x2 == 1500  # the second point
    assert head.y2 == pytest.approx(TOP_BAND + LANE_HEIGHT - LABEL_HEIGHT - LANE_LINE_GAP)
    label = next(p for p in primitives if isinstance(p, Text) and p.role == "annotation")
    assert label.text == "+100%"
    assert label.width == MIN_ARROW_LABEL_WIDTH
    assert label.y == LANE_HEIGHT - LANE_LINE_GAP - LABEL_HEIGHT


def test_a_level_arrow_gets_a_lane_right_of_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    arrow = Annotation("difference", 0, 1, style="level")
    primitives = layout_line(chart, 4000, 10000, (arrow,))
    baseline = primitives[0]
    assert baseline == Line(0, 9000, 2000, 9000, "baseline")  # plot shrinks by the lane
    heads = [p for p in primitives if isinstance(p, Line) and p.arrow]
    assert heads[0].x1 == 2000 + LEVEL_ARROW_INSET


def test_a_value_line_gets_a_lane_right_of_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    value = Annotation("value_line", 0, 0, value=15.0)
    primitives = layout_line(chart, 4000, 10000, (value,))
    helper = next(p for p in primitives if isinstance(p, Line) and p.role == "helper")
    assert helper.y1 == pytest.approx(800 + 5 / 20 * 8200)
    label = next(p for p in primitives if p is not None and isinstance(p, Text) and p.text == "15")
    assert label.x == 2000 + LEVEL_ARROW_INSET
    assert helper.x2 == 2000


def test_axis_break_shortens_the_scale() -> None:
    chart = data(("S", (10.0, 100.0, 20.0)), categories=("A", "B", "C"))
    plain = layout_line(chart, 3000, 10000)
    broken = layout_line(chart, 3000, 10000, (Annotation("axis_break", 0, 0),))
    assert broken != plain
    assert any(isinstance(p, Text) and p.role == "axis" for p in broken) is False
    # the lowest point is drawn lower on the shortened scale
    low_plain = min(p.y for p in plain if isinstance(p, Marker))
    low_broken = min(p.y for p in broken if isinstance(p, Marker))
    assert low_broken > low_plain


@pytest.mark.parametrize(("width", "height"), [(0, 10000), (2000, TOP_BAND + CATEGORY_BAND)])
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_line(data(("S", (1.0,)), categories=("X",)), width, height)


def test_empty_data_yields_nothing() -> None:
    assert layout_line(ChartData((), ()), 1000, 5000) == ()


def test_structure_does_not_depend_on_size() -> None:
    chart = parse(sample_line_state())
    arrows = (
        Annotation("difference", 0, 2),
        Annotation("difference", 1, 0, style="level"),
        Annotation("value_line", 0, 0),
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_line(chart, width, height, arrows, LABELS)
        ]

    assert shape(20000, 6000) == shape(60000, 30000) == shape(20000, 4500)


def test_geometry_stays_inside_the_box() -> None:
    chart = parse(sample_line_state())
    arrows = (Annotation("difference", 0, 5), Annotation("value_line", 0, 0))
    primitives: tuple[Primitive, ...] = layout_line(chart, 24000, 12000, arrows, LABELS)
    for p in primitives:
        if isinstance(p, Marker):
            assert 0 <= p.x <= 24000
            assert 0 <= p.y <= 12000
        elif isinstance(p, Polyline):
            assert all(0 <= x <= 24000 and 0 <= y <= 12000 for x, y in p.points)
        elif isinstance(p, Line):
            assert 0 <= min(p.x1, p.x2) <= 24000
            assert 0 <= max(p.y1, p.y2) <= 12000
        else:
            assert isinstance(p, Text)
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9
