import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_area_state
from librecharts.core.layout.area import (
    CATEGORY_BAND,
    LABEL_HEIGHT,
    LEVEL_ARROW_INSET,
    SERIES_BAND,
    SERIES_LABEL_GAP,
    TOP_BAND,
    layout_area,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import Line, Polygon, Primitive, Text

LABELS = Format(series_names="labels")


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def test_area_golden_geometry() -> None:
    # axis 0..40 over 8200 from y=800; one slot of 1000 with the areas' edges at its centre
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    assert layout_area(chart, "stacked", 1000, 10000) == (
        Line(0, 9000, 1000, 9000, "baseline"),
        Text(0, 9000, 1000, CATEGORY_BAND, "X", "center", "category"),
        Polygon(((500, 6950), (500, 9000)), 0),
        Text(0, 7675, 1000, LABEL_HEIGHT, "10", "center", "value", fill=0),
        Polygon(((500, 800), (500, 6950)), 1),
        Text(0, 3575, 1000, LABEL_HEIGHT, "30", "center", "value", fill=1),
    )


def test_percent_areas_are_full_and_show_their_shares() -> None:
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    primitives = layout_area(chart, "stacked", 1000, 10000, percent=True)
    polygons = [p for p in primitives if isinstance(p, Polygon)]
    assert len(polygons) == 2
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["25%", "75%"]
    # the stack reaches the top of the plot
    assert min(y for p in polygons for _, y in p.points) == pytest.approx(TOP_BAND)


def test_negative_and_empty_values_count_as_zero() -> None:
    chart = data(("A", (-5.0, None)), ("B", (None, 20.0)), categories=("X", "Y"))
    primitives = layout_area(chart, "stacked", 2000, 10000)
    polygons = [p for p in primitives if isinstance(p, Polygon)]
    # series A has no height anywhere, so it draws no area; B fills Y
    assert [p.series for p in polygons] == [1]
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["", "20"]


def test_flat_areas_get_an_empty_inside_label() -> None:
    chart = data(("A", (1.0,)), ("B", (1000.0,)), categories=("X",))
    labels = [
        p.text
        for p in layout_area(chart, "stacked", 1000, 10000)
        if isinstance(p, Text) and p.role == "value"
    ]
    assert labels == ["", "1000"]


def test_a_legend_sits_above_the_plot() -> None:
    chart = data(("A", (10.0,)), ("B", (20.0,)), categories=("X",))
    primitives = layout_area(chart, "stacked", 2000, 10000, fmt=Format(series_names="legend"))
    assert [p.text for p in primitives if isinstance(p, Text) and p.role == "series"] == ["A", "B"]
    assert min(y for p in primitives if isinstance(p, Polygon) for _, y in p.points) >= 800 + 800


def test_series_names_sit_right_of_the_last_area() -> None:
    chart = data(("Revenue", (10.0, 20.0)), ("Costs", (5.0, 8.0)), categories=("A", "B"))
    primitives = layout_area(chart, "stacked", 6000, 10000, fmt=LABELS)
    names = [p for p in primitives if isinstance(p, Text) and p.role == "series"]
    assert {p.text for p in names} == {"Revenue", "Costs"}
    assert all(p.x == 6000 - SERIES_BAND + SERIES_LABEL_GAP for p in names)
    assert names[0].y != names[1].y


def test_the_value_axis_and_gridlines_are_optional() -> None:
    chart = data(("A", (10.0,)), categories=("X",))
    plain = layout_area(chart, "stacked", 3000, 10000)
    with_axis = layout_area(chart, "stacked", 3000, 10000, fmt=Format(axis=True))
    with_grid = layout_area(chart, "stacked", 3000, 10000, fmt=Format(axis=True, gridlines=True))
    assert not any(isinstance(p, Line) and p.role == "axis" for p in plain)
    assert any(isinstance(p, Line) and p.role == "axis" for p in with_axis)
    assert len([p for p in with_grid if isinstance(p, Line) and p.role == "grid"]) == 5


def test_a_value_line_gets_a_lane_right_of_the_plot() -> None:
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    value = Annotation("value_line", 0, 0, value=20.0)
    primitives = layout_area(chart, "stacked", 4000, 10000, (value,))
    helper = next(p for p in primitives if isinstance(p, Line) and p.role == "helper")
    assert helper.y1 == pytest.approx(800 + 20 / 40 * 8200)
    assert helper.x2 == 2000  # the plot shrinks by one lane
    label = next(p for p in primitives if isinstance(p, Text) and p.text == "20")
    assert label.x == 2000 + LEVEL_ARROW_INSET


def test_a_percent_area_chart_draws_no_value_line() -> None:
    chart = data(("A", (10.0,)), categories=("X",))
    value = Annotation("value_line", 0, 0, value=20.0)
    assert layout_area(chart, "stacked", 4000, 10000, (value,), percent=True) == layout_area(
        chart, "stacked", 4000, 10000, percent=True
    )


def test_other_annotations_are_ignored() -> None:
    chart = data(("A", (10.0, 20.0)), categories=("A", "B"))
    arrow = (Annotation("difference", 0, 1),)
    assert layout_area(chart, "stacked", 4000, 10000, arrow) == layout_area(
        chart, "stacked", 4000, 10000
    )


@pytest.mark.parametrize(("width", "height"), [(0, 10000), (1000, TOP_BAND + CATEGORY_BAND)])
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_area(data(("A", (1.0,)), categories=("X",)), "stacked", width, height)


def test_empty_data_yields_nothing() -> None:
    assert layout_area(ChartData((), ()), "stacked", 1000, 5000) == ()


def test_structure_does_not_depend_on_size() -> None:
    chart = parse(sample_area_state())

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""))
            for p in layout_area(chart, "stacked", width, height, fmt=LABELS)
        ]

    assert shape(12000, 6000) == shape(60000, 30000) == shape(9000, 4500)


def test_geometry_stays_inside_the_box() -> None:
    chart = parse(sample_area_state())
    value = Annotation("value_line", 0, 0)
    primitives: tuple[Primitive, ...] = layout_area(
        chart, "stacked", 24000, 12000, (value,), fmt=LABELS
    )
    for p in primitives:
        if isinstance(p, Polygon):
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
