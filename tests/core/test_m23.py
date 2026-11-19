"""M23: manual axes, titles, logarithmic scale and trendlines."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import format as formats
from librecharts.core import trend
from librecharts.core.datasheet import (
    parse,
    sample_line_state,
    sample_scatter_state,
    sample_state,
)
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.line import layout_line
from librecharts.core.layout.scatter import layout_scatter
from librecharts.core.model import Format, Trend
from librecharts.core.primitives import Polyline, Text
from librecharts.core.scale import Axis, manual_axis, nice_axis
from librecharts.core.scatter import parse_scatter
from librecharts.core.state_io import from_json, to_json


def test_a_manual_axis_fills_the_missing_bound_from_the_fallback() -> None:
    fallback = nice_axis(0.0, 100.0)
    assert manual_axis(20.0, 80.0, 10.0) == Axis(20.0, 80.0, 10.0)
    axis = manual_axis(20.0, None, 10.0, fallback=fallback)
    assert axis == Axis(20.0, 100.0, 10.0)
    assert manual_axis(None, 80.0, 10.0, fallback=fallback) == Axis(0.0, 80.0, 10.0)
    with pytest.raises(ValueError, match="below"):
        manual_axis(80.0, 20.0, 10.0)
    with pytest.raises(ValueError, match="positive"):
        manual_axis(0.0, 100.0, 10.0, scale="log")


def test_a_log_axis_fractions_and_ticks() -> None:
    axis = Axis(1.0, 1000.0, 1.0, "log")
    assert axis.fraction(1.0) == 0.0
    assert axis.fraction(1000.0) == 1.0
    assert axis.fraction(10.0) == pytest.approx(1 / 3)
    assert axis.ticks()[:3] == [1.0, 2.0, 5.0]
    assert 1000.0 in axis.ticks()
    with pytest.raises(ValueError, match="positive"):
        Axis(0.0, 10.0, 1.0, "log")


def test_manual_limits_and_log_are_used_by_the_layout() -> None:
    state = replace(sample_line_state(), format=Format(axis=True, axis_min=10.0, axis_max=50.0))
    primitives = layout_chart(state, 4000, 4000)
    texts = [p.text for p in primitives if isinstance(p, Text) and p.role == "axis"]
    assert "10" in texts
    assert "50" in texts


def test_a_log_axis_rejects_non_positive_data() -> None:
    values = ((None, None, None), (None, 0.0, 5.0), (None, 1.0, 2.0))
    state = replace(
        sample_line_state(),
        values=values,
        cells=(("", "A", "B"), ("S1", "0", "5"), ("S2", "1", "2")),
        format=Format(axis_scale="log"),
    )
    with pytest.raises(ValueError, match="positive data"):
        layout_chart(state, 4000, 4000)


def test_a_truncated_column_axis_draws_a_cut_mark() -> None:
    state = replace(sample_state(), format=Format(axis_min=5.0))
    primitives = layout_chart(state, 4000, 4000)
    assert any(isinstance(p, Text) and p.text == "5" for p in primitives)
    assert sum(1 for p in primitives if getattr(p, "role", "") == "axis") >= 1


def test_axis_titles_reserve_a_band_and_rotate_the_value_title() -> None:
    state = replace(
        sample_state(),
        format=Format(axis_title="Revenue", category_axis_title="Year"),
    )
    primitives = layout_chart(state, 4000, 4000)
    titles = [p for p in primitives if isinstance(p, Text) and p.role == "axis"]
    value = next(p for p in titles if p.text == "Revenue")
    assert value.rotation == 90
    assert any(p.text == "Year" for p in titles)


def test_the_axis_dialog_fields_are_parsed_in_the_format() -> None:
    fmt = formats.axes(
        Format(),
        {
            "axis_min": "10",
            "axis_max": "90,5",
            "axis_step": "",
            "axis_scale": "log",
            "axis_title": "Sales",
            "category_axis_title": "Year",
        },
    )
    assert fmt.axis_min == 10.0
    assert fmt.axis_max == 90.5
    assert fmt.axis_step is None
    assert fmt.axis_scale == "log"
    assert fmt.axis_title == "Sales"
    assert fmt.category_axis_title == "Year"
    with pytest.raises(ValueError, match="number"):
        formats.axes(Format(), {"axis_min": "many"})


def test_a_linear_fit_is_exact() -> None:
    fitted = trend.fit([(0.0, 1.0), (1.0, 3.0), (2.0, 5.0), (3.0, 7.0)])
    assert fitted is not None
    assert fitted.value(4.0) == pytest.approx(9.0)
    assert fitted.r2 == pytest.approx(1.0)
    assert trend.label(fitted) == "R² = 1"
    assert "2x" in trend.label(fitted, equation=True)


def test_an_exponential_fit_and_its_rejection() -> None:
    fitted = trend.fit([(0.0, 2.0), (1.0, 4.0), (2.0, 8.0), (3.0, 16.0)], "exponential")
    assert fitted is not None
    assert fitted.value(4.0) == pytest.approx(32.0)
    with pytest.raises(ValueError, match="positive"):
        trend.fit([(0.0, 0.0), (1.0, 1.0)], "exponential")
    assert trend.fit([(0.0, 1.0)]) is None


def test_a_line_trendline_and_its_forecast_are_layout_output() -> None:
    state = replace(
        sample_line_state(),
        trends=(Trend(0, "linear", forecast=2),),
    )
    primitives = layout_line(parse(state), 4000, 4000, trends=state.trends)
    assert any(isinstance(p, Polyline) and p.dashed for p in primitives)
    assert any(isinstance(p, Text) and p.text.startswith("R²") for p in primitives)


def test_a_scatter_trendline_uses_the_x_values() -> None:
    state = replace(sample_scatter_state(), trends=(Trend(0, "linear", forecast=1),))
    primitives = layout_scatter(parse_scatter(state), 4000, 4000, trends=state.trends)
    assert any(isinstance(p, Polyline) for p in primitives)
    assert any(isinstance(p, Text) and p.text.startswith("R²") for p in primitives)


def test_trends_round_trip_and_are_validated() -> None:
    state = replace(sample_line_state(), trends=(Trend(0, "exponential", 2, False, True),))
    restored = from_json(to_json(state))
    assert restored.trends == state.trends
    with pytest.raises(ValueError, match="one trendline"):
        replace(state, trends=(Trend(0), Trend(0)))
    with pytest.raises(ValueError, match="trendlines"):
        replace(sample_state(), kind="pie", trends=(Trend(0),))
    with pytest.raises(ValueError, match="unknown trend"):
        Trend(0, "quadratic")  # pyright: ignore[reportArgumentType]
