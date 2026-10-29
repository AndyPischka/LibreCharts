"""Layout of the M6 format: value axis, gridlines, series names, legend and value lines."""

from dataclasses import replace

import pytest

from librecharts.core.axis_break import Break
from librecharts.core.datasheet import (
    ChartData,
    Series,
    sample_mekko_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.common import format_share, format_value, visible_ticks
from librecharts.core.layout.mekko import layout_mekko
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import Line, Rect, Text
from librecharts.core.scale import Axis
from librecharts.core.waterfall import parse_waterfall


def data(*series: tuple[str, tuple[float | None, ...]], categories: tuple[str, ...]) -> ChartData:
    return ChartData(categories, tuple(Series(n, v) for n, v in series))


def roles(primitives: tuple[object, ...], role: str) -> list[Line]:
    return [p for p in primitives if isinstance(p, Line) and p.role == role]


def labels(primitives: tuple[object, ...], role: str) -> list[str]:
    return [p.text for p in primitives if isinstance(p, Text) and p.role == role]


# Number format


def test_format_value_keeps_todays_rule_by_default() -> None:
    assert format_value(10.0) == "10"
    assert format_value(10.5) == "10.5"
    assert format_value(10.25) == "10.25"
    assert format_value(10.123) == "10.12"
    assert format_value(-0.0) == "0"


def test_format_value_applies_decimals() -> None:
    assert format_value(1.5, Format(decimals=2)) == "1.50"
    assert format_value(1.5, Format(decimals=0)) == "2"


def test_format_value_applies_magnitude_unit_and_separator() -> None:
    fmt = Format(magnitude=3, decimals=1, unit="€", separator=",", language="de")
    assert format_value(1234.5, fmt) == "1,2 Tsd. €"
    assert format_value(1234.5, replace(fmt, magnitude=0, unit="")) == "1234,5"
    assert format_value(1234.5, Format(magnitude=6, language="en")) == "0 M"


def test_a_share_uses_decimals_and_separator_but_no_magnitude() -> None:
    assert format_share(33.3) == "33.3%"
    assert format_share(33.3, Format(decimals=0)) == "33%"
    assert format_share(33.3, Format(separator=",")) == "33,3%"
    assert format_share(0.0) == "0%"


# Axis and gridlines


def test_a_column_chart_can_show_an_axis() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_column(chart, "clustered", 3000, 10000, fmt=Format(axis=True))
    assert Line(1600, 800, 1600, 9000, "axis") in primitives
    assert labels(primitives, "axis") == ["0", "5", "10", "15", "20"]
    assert primitives.index(Line(1600, 800, 1600, 9000, "axis")) == 1  # right after the baseline


def test_gridlines_lie_behind_the_columns() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_column(
        chart, "clustered", 3000, 10000, fmt=Format(axis=True, gridlines=True)
    )
    grids = roles(primitives, "grid")
    assert [g.y1 for g in grids] == [6950, 4900, 2850, 800]
    assert primitives.index(grids[0]) < primitives.index(Line(1600, 800, 1600, 9000, "axis"))


def test_gridlines_alone_are_not_drawn() -> None:
    chart = data(("S", (10.0,)), categories=("A",))
    primitives = layout_column(chart, "clustered", 3000, 10000, fmt=Format(gridlines=True))
    assert not roles(primitives, "grid")
    assert not roles(primitives, "axis")


def test_a_100_percent_column_chart_gets_a_fixed_axis() -> None:
    chart = data(("S", (1.0, 3.0)), categories=("A", "B"))
    primitives = layout_column(chart, "stacked", 3000, 10000, percent=True, fmt=Format(axis=True))
    assert labels(primitives, "axis") == ["0", "20", "40", "60", "80", "100"]


def test_a_bar_chart_puts_the_axis_below_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_bar(chart, "clustered", 8200, 3000, fmt=Format(axis=True))
    assert Line(3000, 2300, 7000, 2300, "axis") in primitives
    assert labels(primitives, "axis") == ["0", "5", "10", "15", "20"]
    assert primitives.index(Line(3000, 2300, 7000, 2300, "axis")) == 1


def test_a_waterfall_chart_can_show_an_axis() -> None:
    primitives = layout_waterfall(
        parse_waterfall(sample_waterfall_state()), 12000, 8000, fmt=Format(axis=True)
    )
    assert labels(primitives, "axis") == ["0", "50", "100", "150"]


def test_a_units_mekko_can_show_an_axis() -> None:
    primitives = layout_mekko(
        parse_mekko(sample_mekko_state()), 12000, 8000, percent=False, fmt=Format(axis=True)
    )
    assert "0" in labels(primitives, "axis")
    assert "80" in labels(primitives, "axis")


def test_ticks_inside_an_axis_break_are_left_out() -> None:
    cut = Break(4.0, 8.0)
    assert visible_ticks(Axis(0.0, 10.0, 2.0), cut) == [0.0, 2.0, 4.0, 8.0, 10.0]
    assert visible_ticks(Axis(0.0, 10.0, 2.0)) == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]


def test_the_axis_break_marks_the_axis_line() -> None:
    chart = data(("S", (10.0, 100.0)), categories=("A", "B"))
    annotation = Annotation("axis_break", 0, 0, lower=20.0, upper=90.0)
    primitives = layout_column(
        chart, "clustered", 3000, 10000, (annotation,), fmt=Format(axis=True)
    )
    assert roles(primitives, "axis")  # the line, the ticks and the two break lines


# Series names


def test_series_labels_sit_right_of_the_plot() -> None:
    chart = data(("A", (10.0, 20.0)), ("B", (5.0, 5.0)), categories=("X", "Y"))
    primitives = layout_column(chart, "stacked", 6000, 10000, fmt=Format(series_names="labels"))
    assert labels(primitives, "series") == ["A", "B"]
    assert all(
        p.x >= 6000 - 2600 - 1e-9 for p in primitives if isinstance(p, Text) and p.role == "series"
    )


def test_a_legend_sits_above_the_plot() -> None:
    chart = data(("A", (10.0,)), ("B", (5.0,)), categories=("X",))
    primitives = layout_column(chart, "stacked", 6000, 10000, fmt=Format(series_names="legend"))
    assert labels(primitives, "series") == ["A", "B"]
    assert all(p.y < 800 for p in primitives if isinstance(p, Text) and p.role == "series")
    assert isinstance(primitives[0], Rect)


def test_no_series_names_by_default() -> None:
    chart = data(("A", (10.0,)), categories=("X",))
    assert not roles(layout_column(chart, "stacked", 6000, 10000), "series")
    assert not roles(layout_column(chart, "stacked", 6000, 10000, fmt=Format()), "series")


def test_a_bar_chart_shows_series_labels_right_of_the_bars() -> None:
    chart = data(("A", (10.0,)), ("B", (5.0,)), categories=("X",))
    primitives = layout_bar(chart, "stacked", 9000, 2000, fmt=Format(series_names="labels"))
    assert labels(primitives, "series") == ["A", "B"]


def test_a_mekko_can_hide_its_series_names_and_show_a_legend() -> None:
    state = sample_mekko_state()
    hidden = layout_mekko(parse_mekko(state), 12000, 8000, fmt=Format(series_names="none"))
    assert not roles(hidden, "series")
    legend = layout_mekko(parse_mekko(state), 12000, 8000, fmt=Format(series_names="legend"))
    assert labels(legend, "series") == ["Product A", "Product B", "Product C"]
    assert all(p.y < 800 for p in legend if isinstance(p, Text) and p.role == "series")


# Value lines


def test_a_value_line_is_drawn_at_its_value_with_a_label() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    annotation = Annotation("value_line", 0, 0, value=12.0)
    primitives = layout_column(chart, "clustered", 6000, 10000, (annotation,))
    assert Line(0, 4080, 4000, 4080, "helper") in primitives
    assert "12" in labels(primitives, "annotation")


def test_a_value_line_without_a_value_marks_the_average() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    primitives = layout_column(chart, "clustered", 6000, 10000, (Annotation("value_line", 0, 0),))
    assert "15" in labels(primitives, "annotation")


def test_several_value_lines_get_one_lane_each() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    notes = (Annotation("value_line", 0, 0, value=12.0), Annotation("value_line", 0, 0, value=18.0))
    primitives = layout_column(chart, "clustered", 8000, 10000, notes)
    assert labels(primitives, "annotation") == ["12", "18"]


def test_a_bar_value_line_is_vertical_below_the_plot() -> None:
    chart = data(("S", (10.0, 20.0)), categories=("A", "B"))
    annotation = Annotation("value_line", 0, 0, value=12.0)
    primitives = layout_bar(chart, "clustered", 8200, 5000, (annotation,))
    line = next(p for p in primitives if isinstance(p, Line) and p.role == "helper")
    assert line.x1 == line.x2
    assert "12" in labels(primitives, "annotation")


def test_a_waterfall_value_line_uses_the_step_levels() -> None:
    state = sample_waterfall_state()
    annotation = Annotation("value_line", 0, 0, value=120.0)
    primitives = layout_waterfall(parse_waterfall(state), 12000, 8000, (annotation,))
    assert labels(primitives, "annotation") == ["120"]


def test_a_value_line_is_not_drawn_without_categories() -> None:
    chart = data(("S", (10.0,)), categories=())
    primitives = layout_column(chart, "clustered", 6000, 10000, (Annotation("value_line", 0, 0),))
    assert primitives == ()


# The whole chart


def test_the_format_reaches_the_layout_through_the_state() -> None:
    state = replace(
        state_from_table("column", "clustered", [[None, "A", "B"], ["S", 10, 20]]),
        format=Format(axis=True, series_names="legend", decimals=1),
    )
    primitives = layout_chart(state, 8000, 10000)
    assert labels(primitives, "axis") == ["0.0", "5.0", "10.0", "15.0", "20.0"]
    assert labels(primitives, "series") == ["S"]


def test_the_primitive_structure_does_not_depend_on_the_size() -> None:
    state = replace(
        state_from_table("column", "stacked", [[None, "A", "B"], ["S", 10, 20]]),
        format=Format(axis=True, gridlines=True, series_names="labels"),
        annotations=(
            Annotation("value_line", 0, 0, value=12.0),
            Annotation("difference", 0, 1),
        ),
    )

    def structure(width: float, height: float) -> list[tuple[str, str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", ""), getattr(p, "text", ""))
            for p in layout_chart(state, width, height)
        ]

    assert structure(8000, 10000) == structure(20000, 7000)


@pytest.mark.parametrize("kind", ["column", "bar", "waterfall", "mekko"])
def test_every_layout_accepts_the_format(kind: str) -> None:
    if kind == "waterfall":
        primitives = layout_waterfall(
            parse_waterfall(sample_waterfall_state()), 12000, 8000, fmt=Format(axis=True)
        )
    elif kind == "mekko":
        primitives = layout_mekko(
            parse_mekko(sample_mekko_state()), 12000, 8000, fmt=Format(series_names="none")
        )
    elif kind == "bar":
        chart = data(("S", (1.0, 2.0)), categories=("A", "B"))
        primitives = layout_bar(chart, "stacked", 9000, 3000, fmt=Format(series_names="legend"))
    else:
        chart = data(("S", (1.0, 2.0)), categories=("A", "B"))
        primitives = layout_column(chart, "stacked", 6000, 10000, fmt=Format(series_names="legend"))
    assert primitives
