"""M24: dumbbell, bullet, Pareto, funnel and box plot charts."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import boxplot, bullet
from librecharts.core.datasheet import (
    parse,
    sample_boxplot_state,
    sample_bullet_state,
    sample_dumbbell_state,
    sample_funnel_state,
    sample_state,
    state_from_table,
)
from librecharts.core.layout.boxplot import layout_boxplot
from librecharts.core.layout.bullet import layout_bullet
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.dumbbell import layout_dumbbell
from librecharts.core.layout.funnel import layout_funnel
from librecharts.core.layout.pareto import layout_pareto
from librecharts.core.model import ChartState
from librecharts.core.options import changed as option
from librecharts.core.primitives import Line, Marker, Polygon, Rect, Text
from librecharts.core.state_io import from_json, to_json


def test_the_new_sample_data_sheets_parse() -> None:
    assert len(bullet.parse(sample_bullet_state()).rows) == 3
    assert len(boxplot.parse(sample_boxplot_state()).rows) == 3
    assert len(sample_funnel_state().values) == 2


def test_a_bullet_row_needs_an_actual_value_and_a_maximum() -> None:
    state = state_from_table(
        "bullet", "stacked", [["KPI", "Actual", "Target", "Max"], ["A", None, 1, 10]]
    )
    with pytest.raises(bullet.BulletError, match="bullet_empty"):
        bullet.parse(state)
    state = state_from_table(
        "bullet", "stacked", [["KPI", "Actual", "Target", "Max"], ["A", -1, 1, 10]]
    )
    with pytest.raises(bullet.BulletError, match="bullet_negative"):
        bullet.parse(state)


def test_a_box_summary_must_be_ordered() -> None:
    state = state_from_table(
        "boxplot", "stacked", [["G", "Min", "Q1", "Median", "Q3", "Max"], ["A", 0, 5, 4, 6, 10]]
    )
    with pytest.raises(boxplot.BoxError, match="boxplot_order"):
        boxplot.parse(state)


def test_every_new_kind_draws_primitives() -> None:
    for state in (
        sample_dumbbell_state(),
        sample_bullet_state(),
        sample_funnel_state(),
        sample_boxplot_state(),
    ):
        primitives = layout_chart(state, 8000, 6000)
        assert primitives, state.kind
        assert not any(isinstance(p, Polygon) for p in primitives)


def test_a_dumbbell_chart_connects_two_points_per_category() -> None:
    primitives = layout_dumbbell(parse(sample_dumbbell_state()), 8000, 6000)
    assert len([p for p in primitives if isinstance(p, Marker)]) == 8
    assert len([p for p in primitives if isinstance(p, Line) and p.role == "connector"]) == 4
    assert len([p for p in primitives if isinstance(p, Text) and p.role == "value"]) == 8


def test_a_vertical_dumbbell_puts_the_lower_label_below_its_point() -> None:
    primitives = layout_dumbbell(parse(sample_dumbbell_state()), 8000, 6000, horizontal=False)
    markers = [p for p in primitives if isinstance(p, Marker)]
    labels = [p for p in primitives if isinstance(p, Text) and p.role == "value"]
    categories = [p for p in primitives if isinstance(p, Text) and p.role == "category"]
    assert len(markers) == len(labels) == 8
    for number in range(0, len(markers), 2):
        upper, lower = sorted(markers[number : number + 2], key=lambda p: p.y)
        upper_label, lower_label = sorted(labels[number : number + 2], key=lambda p: p.y)
        assert upper_label.y + upper_label.height < upper.y
        assert lower_label.y > lower.y
        # the label hangs below the plot, but stops above the category names
        assert lower_label.y + lower_label.height <= categories[number // 2].y


def test_a_bullet_chart_has_a_bar_and_a_target_tick_per_row() -> None:
    data = bullet.parse(sample_bullet_state())
    primitives = layout_bullet(data, 8000, 6000)
    assert len([p for p in primitives if isinstance(p, Rect)]) == 3
    assert len([p for p in primitives if isinstance(p, Line) and p.role == "annotation"]) == 3


def test_a_funnel_bar_width_follows_the_value() -> None:
    primitives = layout_funnel(parse(sample_funnel_state()), 8000, 6000)
    bars = [p for p in primitives if isinstance(p, Rect)]
    assert bars[0].width > bars[-1].width
    assert bars[-1].x > 0  # centred


def test_a_box_plot_draws_a_box_median_and_whiskers() -> None:
    primitives = layout_boxplot(boxplot.parse(sample_boxplot_state()), 8000, 6000)
    assert len([p for p in primitives if isinstance(p, Rect)]) == 3
    assert len([p for p in primitives if isinstance(p, Marker)]) == 2


def pareto_state() -> ChartState:
    return replace(
        state_from_table(
            "column",
            "clustered",
            [[None, "A", "B", "C"], ["Sales", 30, 20, 10]],
        ),
        pareto=True,
    )


def test_a_pareto_chart_sorts_descending_and_adds_the_cumulative_line() -> None:
    state = pareto_state()
    primitives = layout_pareto(parse(state), 8000, 6000)
    bars = [p for p in primitives if isinstance(p, Rect)]
    assert bars[0].height >= bars[1].height
    assert any(isinstance(p, Marker) for p in primitives)
    assert any(isinstance(p, Line) and p.role == "helper" for p in primitives)


def test_the_pareto_switch_clears_incompatible_options() -> None:
    state = option(pareto_state(), "pareto=false")
    state = option(state, "pareto=true")
    assert state.pareto
    assert state.grouping == "clustered"
    assert not state.percent
    assert option(state, "pareto=false").pareto is False


def test_pareto_is_validated_and_round_trips() -> None:
    state = pareto_state()
    assert from_json(to_json(state)).pareto
    with pytest.raises(ValueError, match="Pareto"):
        replace(state, grouping="stacked", percent=True)
    with pytest.raises(ValueError, match="Pareto"):
        replace(sample_state(), kind="line", pareto=True)


def test_the_new_kinds_round_trip() -> None:
    for state in (
        sample_dumbbell_state(),
        sample_bullet_state(),
        sample_funnel_state(),
        sample_boxplot_state(),
    ):
        restored = from_json(to_json(state))
        assert restored.kind == state.kind
        assert restored.values == state.values


def test_a_dumbbell_switches_between_horizontal_and_vertical() -> None:
    state = sample_dumbbell_state()
    vertical = option(state, "horizontal=false")
    assert vertical.horizontal is False
    horizontal = option(vertical, "horizontal=true")
    assert horizontal.horizontal
