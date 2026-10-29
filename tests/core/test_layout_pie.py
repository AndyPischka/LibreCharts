import math
from dataclasses import replace

import pytest

from librecharts.core.datasheet import ChartData, Series, parse, sample_pie_state
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.pie import (
    CATEGORY_BAND,
    DOUGHNUT_HOLE,
    OUTSIDE_RADIUS,
    layout_pie,
)
from librecharts.core.model import Format
from librecharts.core.primitives import Polygon, Rect, Text


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def centre(text: Text) -> tuple[float, float]:
    return text.x + text.width / 2, text.y + text.height / 2


def test_segments_follow_series_order_and_fill_the_whole_pie() -> None:
    chart = data(("A", (1.0,)), ("B", (3.0,)), categories=("X",))
    primitives = layout_pie(chart, False, 6000, 6000)
    polygons = [p for p in primitives if isinstance(p, Polygon)]
    assert [p.series for p in polygons] == [0, 1]
    # A takes 90 degrees from 12 o'clock, B the remaining 270
    assert len(polygons[0].points) == 1 + 90 + 1
    assert len(polygons[1].points) == 1 + 270 + 1
    first_arc = polygons[0].points[1]
    centre_point = polygons[0].points[0]
    assert first_arc[0] == pytest.approx(centre_point[0])  # straight up from the centre
    assert first_arc[1] < centre_point[1]


def test_shares_are_labelled_inside_wide_and_outside_narrow_segments() -> None:
    chart = data(("A", (97.0,)), ("B", (3.0,)), categories=("X",))
    primitives = layout_pie(chart, False, 8000, 8000)
    labels = {p.text: p for p in primitives if isinstance(p, Text) and p.role == "value"}
    assert set(labels) == {"97%", "3%"}
    assert labels["97%"].fill == 0  # inside: text contrasts with the segment colour
    assert labels["3%"].fill is None  # outside: plain text on the slide
    polygon = next(p for p in primitives if isinstance(p, Polygon))
    cx, cy = polygon.points[0]
    radius = math.hypot(polygon.points[1][0] - cx, polygon.points[1][1] - cy)
    assert math.hypot(*(a - b for a, b in zip(centre(labels["3%"]), (cx, cy), strict=True))) == (
        pytest.approx(radius * OUTSIDE_RADIUS)
    )
    assert math.hypot(*(a - b for a, b in zip(centre(labels["97%"]), (cx, cy), strict=True))) < (
        radius
    )


def test_a_segment_of_exactly_the_minimum_angle_is_labelled_inside() -> None:
    chart = data(("A", (20.0,)), ("B", (340.0,)), categories=("X",))  # 20 degrees of 360
    primitives = layout_pie(chart, False, 8000, 8000)
    label = next(p for p in primitives if isinstance(p, Text) and p.text == "5.6%")
    assert label.fill == 0


def test_negative_and_empty_values_draw_no_segment() -> None:
    chart = data(("A", (5.0,)), ("B", (-3.0,)), ("C", (None,)), ("D", (5.0,)), categories=("X",))
    primitives = layout_pie(chart, False, 8000, 8000)
    assert [p.series for p in primitives if isinstance(p, Polygon)] == [0, 3]
    assert [p.text for p in primitives if isinstance(p, Text) and p.role == "value"] == [
        "50%",
        "50%",
    ]


def test_every_category_gets_its_own_pie_and_name() -> None:
    chart = data(("A", (1.0, 2.0)), ("B", (1.0, 2.0)), categories=("2024", "2025"))
    primitives = layout_pie(chart, False, 12000, 6000)
    names = [p for p in primitives if isinstance(p, Text) and p.role == "category"]
    assert [(p.text, p.x, p.width) for p in names] == [("2024", 0, 6000), ("2025", 6000, 6000)]
    assert all(p.y == 6000 - CATEGORY_BAND for p in names)
    centres = sorted({p.points[0][0] for p in primitives if isinstance(p, Polygon)})
    assert centres == [3000, 9000]


def test_a_category_without_positive_values_is_an_empty_slot() -> None:
    chart = data(("A", (1.0, None)), categories=("X", "Y"))
    primitives = layout_pie(chart, False, 12000, 6000)
    assert len([p for p in primitives if isinstance(p, Polygon)]) == 1
    assert len([p for p in primitives if isinstance(p, Text) and p.role == "category"]) == 2


def test_a_doughnut_has_a_hole_with_the_sum() -> None:
    chart = data(("A", (10.0,)), ("B", (30.0,)), categories=("X",))
    primitives = layout_pie(chart, True, 8000, 8000)
    total = next(p for p in primitives if isinstance(p, Text) and p.role == "total")
    assert total.text == "40"
    polygons = [p for p in primitives if isinstance(p, Polygon)]
    cx = total.x + total.width / 2
    cy = total.y + total.height / 2
    radii = sorted({round(math.hypot(x - cx, y - cy)) for p in polygons for x, y in p.points})
    assert radii[0] == pytest.approx(radii[-1] * DOUGHNUT_HOLE, abs=1)
    assert total.width == pytest.approx(2 * radii[0], abs=2)
    # no point of the ring lies in the hole
    assert all(math.hypot(x - cx, y - cy) >= radii[0] - 1 for p in polygons for x, y in p.points)


def test_a_pie_has_no_total_label() -> None:
    chart = data(("A", (10.0,)), categories=("X",))
    assert not any(
        isinstance(p, Text) and p.role == "total" for p in layout_pie(chart, False, 8000, 8000)
    )


def test_the_doughnut_total_uses_the_number_format() -> None:
    chart = data(("A", (1500.0,)), categories=("X",))
    fmt = Format(magnitude=3, unit="EUR", language="en")
    primitives = layout_pie(chart, True, 8000, 8000, fmt)
    assert next(p for p in primitives if isinstance(p, Text) and p.role == "total").text == (
        "1.5 k EUR"
    )


def test_series_names_as_labels_make_a_legend_column_right_of_the_pies() -> None:
    chart = data(("A", (1.0,)), ("B", (2.0,)), categories=("X",))
    primitives = layout_pie(chart, False, 10000, 6000, Format(series_names="labels"))
    swatches = [p for p in primitives if isinstance(p, Rect)]
    names = [p for p in primitives if isinstance(p, Text) and p.role == "series"]
    assert [s.series for s in swatches] == [0, 1]
    assert [n.text for n in names] == ["A", "B"]
    assert all(n.x > 10000 - 2600 for n in names)
    assert names[0].y < names[1].y


def test_a_legend_goes_above_the_pies() -> None:
    chart = data(("A", (1.0,)), ("B", (2.0,)), categories=("X",))
    primitives = layout_pie(chart, False, 10000, 6000, Format(series_names="legend"))
    assert [p.text for p in primitives if isinstance(p, Text) and p.role == "series"] == ["A", "B"]
    top = min(y for p in primitives if isinstance(p, Polygon) for _, y in p.points)
    assert top > 800


def test_labels_stay_inside_the_chart_box() -> None:
    chart = data(("A", (1.0, 5.0)), ("B", (99.0, 5.0)), categories=("X", "Y"))
    primitives = layout_pie(chart, False, 12000, 6000)
    for p in primitives:
        if isinstance(p, Text):
            assert p.x >= -1e-6
            assert p.x + p.width <= 12000 + 1e-6
            assert p.y >= -1e-6
            assert p.y + p.height <= 6000 + 1e-6


def test_the_structure_does_not_depend_on_the_size() -> None:
    chart = parse(sample_pie_state())

    def shape(width: float, height: float) -> list[tuple[str, int]]:
        return [
            (type(p).__name__, len(getattr(p, "points", ())))
            for p in layout_pie(chart, True, width, height)
        ]

    assert shape(12000, 7000) == shape(5000, 4000) == shape(30000, 9000)


def test_an_empty_chart_has_no_primitives() -> None:
    assert layout_pie(ChartData((), ()), False, 8000, 8000) == ()


def test_too_small_a_box_is_rejected() -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_pie(data(("A", (1.0,)), categories=("X",)), False, 1000, 1000)


def test_layout_chart_draws_pies_and_doughnuts_from_the_state() -> None:
    state = sample_pie_state()
    pie = layout_chart(state, 12000, 7000)
    doughnut = layout_chart(replace(state, doughnut=True), 12000, 7000)
    assert any(isinstance(p, Polygon) for p in pie)
    assert not any(isinstance(p, Text) and p.role == "total" for p in pie)
    assert any(isinstance(p, Text) and p.role == "total" for p in doughnut)
