from dataclasses import replace

import pytest

from librecharts.core import samescale
from librecharts.core.datasheet import (
    sample_area_state,
    sample_line_state,
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
)
from librecharts.core.layout.area import layout_area
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.chart import display_data, layout_chart
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.line import layout_line
from librecharts.core.layout.mekko import layout_mekko
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation
from librecharts.core.primitives import BACKGROUND, Line, Marker, Polygon, Rect
from librecharts.core.waterfall import parse_waterfall

WIDTH, HEIGHT = 12000.0, 7000.0


def half(state: object) -> float:
    length = samescale.natural_length_per_unit(state, WIDTH, HEIGHT)  # pyright: ignore[reportArgumentType]
    assert length is not None
    return length / 2


def first_rect(primitives: tuple[object, ...], series: int) -> Rect:
    rect = next(p for p in primitives if isinstance(p, Rect) and p.series == series)
    return rect


def baseline(primitives: tuple[object, ...]) -> Line:
    return next(p for p in primitives if isinstance(p, Line) and p.role == "baseline")


def test_a_column_group_anchors_the_scale_and_halves_the_columns() -> None:
    state = sample_state()
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    assert baseline(natural) == baseline(scaled)
    assert first_rect(scaled, 0).height == pytest.approx(first_rect(natural, 0).height / 2)


def test_a_bar_group_anchors_the_scale_and_halves_the_bars() -> None:
    state = replace(sample_state(), kind="bar")
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    assert baseline(natural) == baseline(scaled)
    assert first_rect(scaled, 0).width == pytest.approx(first_rect(natural, 0).width / 2)


def test_a_line_group_halves_the_distance_from_the_baseline() -> None:
    state = sample_line_state()
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    natural_marker = next(p for p in natural if isinstance(p, Marker))
    scaled_marker = next(p for p in scaled if isinstance(p, Marker))
    assert scaled_marker.x == natural_marker.x
    assert baseline(natural).y1 - scaled_marker.y == pytest.approx(
        (baseline(natural).y1 - natural_marker.y) / 2
    )


def test_an_area_group_stays_lower() -> None:
    state = sample_area_state()
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    natural_top = min(y for p in natural if isinstance(p, Polygon) for _, y in p.points)
    scaled_top = min(y for p in scaled if isinstance(p, Polygon) for _, y in p.points)
    assert natural_top < scaled_top


def test_a_waterfall_group_stays_lower() -> None:
    state = sample_waterfall_state()
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    assert min(p.y for p in natural if isinstance(p, Rect)) < min(
        p.y for p in scaled if isinstance(p, Rect)
    )


def test_a_units_mekko_group_halves_its_columns() -> None:
    state = replace(sample_mekko_state(), percent=False)
    data = parse_mekko(state)
    natural = layout_mekko(data, WIDTH, HEIGHT, False, state.format)
    scaled = layout_mekko(data, WIDTH, HEIGHT, False, state.format, half(state))
    assert max(p.height for p in natural if isinstance(p, Rect)) == pytest.approx(
        max(p.height for p in scaled if isinstance(p, Rect)) * 2
    )


def test_a_percent_mekko_ignores_a_length_per_unit() -> None:
    state = sample_mekko_state()
    data = parse_mekko(state)
    assert layout_mekko(data, WIDTH, HEIGHT, True, state.format) == layout_mekko(
        data, WIDTH, HEIGHT, True, state.format, 1.0
    )


def test_an_axis_break_is_not_drawn_in_a_scale_group() -> None:
    state = replace(
        sample_state(),
        annotations=(Annotation("axis_break", 0, 0, lower=10.0, upper=20.0),),
    )
    natural = layout_chart(state, WIDTH, HEIGHT)
    scaled = layout_chart(state, WIDTH, HEIGHT, half(state))
    assert any(isinstance(p, Rect) and p.series == BACKGROUND for p in natural)
    assert not any(isinstance(p, Rect) and p.series == BACKGROUND for p in scaled)


def test_each_layout_accepts_a_length_per_unit_directly() -> None:
    column = sample_state()
    data, annotations = display_data(column)
    length = half(column)
    assert layout_column(
        data, column.grouping, WIDTH, HEIGHT, annotations, fmt=column.format, length_per_unit=length
    )
    bar = replace(column, kind="bar")
    data, annotations = display_data(bar)
    assert layout_bar(
        data, bar.grouping, WIDTH, HEIGHT, annotations, fmt=bar.format, length_per_unit=length
    )
    line_state = sample_line_state()
    data, annotations = display_data(line_state)
    assert layout_line(data, WIDTH, HEIGHT, annotations, line_state.format, length)
    area_state = sample_area_state()
    data, annotations = display_data(area_state)
    assert layout_area(
        data,
        area_state.grouping,
        WIDTH,
        HEIGHT,
        annotations,
        fmt=area_state.format,
        length_per_unit=length,
    )
    waterfall_state = sample_waterfall_state()
    assert layout_waterfall(
        parse_waterfall(waterfall_state),
        WIDTH,
        HEIGHT,
        waterfall_state.annotations,
        waterfall_state.format,
        length,
    )
