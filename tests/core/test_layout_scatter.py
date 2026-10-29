import math

import pytest

from librecharts.core.datasheet import sample_scatter_state, state_from_table
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.scatter import layout_scatter
from librecharts.core.model import Annotation, ChartState, Format
from librecharts.core.primitives import (
    MARKER_SIZE,
    Bubble,
    Line,
    Marker,
    Primitive,
    Rect,
    Text,
)
from librecharts.core.scatter import ScatterData, parse_scatter


def chart(*rows: tuple[object, ...]) -> ScatterData:
    table: list[list[object]] = [["Label", "X", "Y", "Size", "Group"], *[list(r) for r in rows]]
    return parse_scatter(state_from_table("scatter", "stacked", table))  # pyright: ignore[reportArgumentType]


def texts(primitives: tuple[Primitive, ...], role: str) -> list[Text]:
    return [p for p in primitives if isinstance(p, Text) and p.role == role]


def test_both_axes_are_always_drawn() -> None:
    primitives = layout_scatter(chart(("A", 10, 100, None, None)), 12000, 8000)
    axes = [p for p in primitives if isinstance(p, Line) and p.role == "axis"]
    assert len(axes) == 2
    assert [t.text for t in texts(primitives, "axis")]  # tick labels exist


def test_axes_do_not_have_to_include_zero() -> None:
    data = chart(("A", 100, 1000, None, None), ("B", 120, 1100, None, None))
    primitives = layout_scatter(data, 12000, 8000)
    ticks = [float(t.text) for t in texts(primitives, "axis")]
    assert min(ticks) >= 100


def test_markers_sit_where_their_values_are() -> None:
    data = chart(("A", 0, 0, None, None), ("B", 10, 10, None, None))
    primitives = layout_scatter(data, 12000, 8000)
    low, high = [p for p in primitives if isinstance(p, Marker)]
    assert high.x > low.x
    assert high.y < low.y  # y grows upwards
    assert low.x == pytest.approx(1600)  # the left edge of the plot, right of the axis band


def test_points_of_one_group_share_a_series_index_and_a_legend_entry() -> None:
    primitives = layout_scatter(parse_scatter(sample_scatter_state()), 14000, 8000)
    assert [m.series for m in primitives if isinstance(m, Marker)] == [0, 0, 0, 0, 1, 1, 1, 1]
    assert [t.text for t in texts(primitives, "series")] == ["Group 1", "Group 2"]
    assert [r.series for r in primitives if isinstance(r, Rect)] == [0, 1]


def test_without_group_names_there_is_no_legend() -> None:
    primitives = layout_scatter(chart(("A", 1, 2, None, None)), 12000, 8000)
    assert not texts(primitives, "series")


def test_bubble_areas_are_proportional_to_the_sizes() -> None:
    data = chart(("A", 1, 1, 100, None), ("B", 2, 2, 25, None), ("C", 3, 3, 4, None))
    bubbles = [p for p in layout_scatter(data, 12000, 8000) if isinstance(p, Bubble)]
    assert len(bubbles) == 3
    by_size = sorted(bubbles, key=lambda b: -b.diameter)
    areas = [math.pi * (b.diameter / 2) ** 2 for b in by_size]
    assert areas[0] / areas[1] == pytest.approx(4)
    assert areas[0] / areas[2] == pytest.approx(25)


def test_the_largest_bubble_is_a_share_of_the_shorter_plot_side() -> None:
    data = chart(("A", 1, 1, 50, None), ("B", 2, 2, 5, None))
    wide = [p for p in layout_scatter(data, 20000, 8000) if isinstance(p, Bubble)]
    tall = [p for p in layout_scatter(data, 20000, 14000) if isinstance(p, Bubble)]
    assert max(b.diameter for b in tall) > max(b.diameter for b in wide)
    plot_height = 8000 - 600 - 1000
    assert max(b.diameter for b in wide) == pytest.approx(0.12 * plot_height)


def test_big_bubbles_are_drawn_first_and_sizeless_points_stay_markers() -> None:
    data = chart(("S", 1, 1, 5, None), ("L", 2, 2, 50, None), ("M", 3, 3, None, None))
    primitives = layout_scatter(data, 12000, 8000)
    bubbles = [p for p in primitives if isinstance(p, Bubble)]
    assert [b.diameter for b in bubbles] == sorted((b.diameter for b in bubbles), reverse=True)
    assert len([p for p in primitives if isinstance(p, Marker)]) == 1


def test_labels_sit_right_of_their_points_and_empty_labels_are_left_out() -> None:
    data = chart(("A", 1, 1, None, None), ("", 2, 2, None, None))
    primitives = layout_scatter(data, 12000, 8000)
    (label,) = texts(primitives, "value")
    marker = next(p for p in primitives if isinstance(p, Marker))
    assert label.text == "A"
    assert label.align == "left"
    assert label.x == pytest.approx(marker.x + MARKER_SIZE / 2 + 100)
    assert label.y + label.height / 2 == pytest.approx(marker.y)


def test_gridlines_are_optional_and_leave_out_the_axis_ticks() -> None:
    data = chart(("A", 0, 0, None, None), ("B", 10, 10, None, None))
    plain = layout_scatter(data, 12000, 8000)
    grid = layout_scatter(data, 12000, 8000, fmt=Format(gridlines=True))
    assert not any(isinstance(p, Line) and p.role == "grid" for p in plain)
    lines = [p for p in grid if isinstance(p, Line) and p.role == "grid"]
    assert lines
    assert any(p.x1 == p.x2 for p in lines)  # vertical
    assert any(p.y1 == p.y2 for p in lines)  # horizontal


def test_a_value_line_marks_a_y_level_and_extends_the_axis() -> None:
    data = chart(("A", 1, 10, None, None), ("B", 2, 20, None, None))
    line = Annotation("value_line", 0, 0, value=50.0)
    primitives = layout_scatter(data, 12000, 8000, (line,))
    (helper,) = [p for p in primitives if isinstance(p, Line) and p.role == "helper"]
    assert helper.y1 == helper.y2
    assert helper.y1 >= 600  # inside the plot although 50 is above the data
    assert [t.text for t in texts(primitives, "annotation")] == ["50"]


def test_a_value_line_without_value_is_the_average() -> None:
    data = chart(("A", 1, 10, None, None), ("B", 2, 20, None, None))
    primitives = layout_scatter(data, 12000, 8000, (Annotation("value_line", 0, 0),))
    assert [t.text for t in texts(primitives, "annotation")] == ["15"]


def test_the_structure_does_not_depend_on_the_size() -> None:
    state: ChartState = sample_scatter_state()

    def kinds(width: float, height: float) -> list[str]:
        return [type(p).__name__ for p in layout_chart(state, width, height)]

    assert kinds(14000, 8000) == kinds(9000, 5000) == kinds(30000, 12000)


def test_an_empty_chart_has_no_primitives() -> None:
    assert layout_scatter(ScatterData((), ()), 12000, 8000) == ()


def test_too_small_a_box_is_rejected() -> None:
    with pytest.raises(ValueError, match="too small"):
        layout_scatter(chart(("A", 1, 1, None, None)), 2000, 2000)
