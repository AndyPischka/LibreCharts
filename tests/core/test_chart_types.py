"""How pie, scatter and butterfly charts plug into the shared modules (M9, ADR 0018)."""

from dataclasses import replace

import pytest

from librecharts.core import annotations as notes
from librecharts.core import samescale, value_line
from librecharts.core.datasheet import (
    sample_butterfly_state,
    sample_pie_state,
    sample_scatter_state,
    sample_state,
)
from librecharts.core.format import default_format, format_options, settled, supports
from librecharts.core.menu import PROTOCOL, chart_menu
from librecharts.core.model import Annotation, ChartState, Format
from librecharts.core.options import (
    changed,
    sort_options,
    sort_toggle,
    variants,
)
from librecharts.core.panel import content


def titles(state: ChartState) -> list[str]:
    return [item.title for item in chart_menu(state, "en-US").children]


# --- model -------------------------------------------------------------------------------------


def test_only_a_pie_chart_can_be_a_doughnut() -> None:
    assert replace(sample_pie_state(), doughnut=True).doughnut
    with pytest.raises(ValueError, match="doughnut"):
        replace(sample_butterfly_state(), doughnut=True)


def test_a_butterfly_chart_can_be_sorted_but_a_pie_or_scatter_chart_cannot() -> None:
    assert replace(sample_butterfly_state(), sort="descending").sort == "descending"
    for state in (sample_pie_state(), sample_scatter_state()):
        with pytest.raises(ValueError, match="cannot be sorted"):
            replace(state, sort="descending")


@pytest.mark.parametrize(
    "state", [sample_pie_state(), sample_scatter_state(), sample_butterfly_state()]
)
def test_the_new_kinds_have_no_100_percent_variant(state: ChartState) -> None:
    with pytest.raises(ValueError, match="percent"):
        replace(state, percent=True)


# --- options -----------------------------------------------------------------------------------


def test_a_pie_chart_switches_between_pie_and_doughnut() -> None:
    pie = sample_pie_state()
    assert [(s.title, s.current) for s in variants(pie)] == [
        ("menu_pie", True),
        ("menu_doughnut", False),
    ]
    doughnut = changed(pie, "doughnut=true")
    assert doughnut.doughnut
    assert [s.current for s in variants(doughnut)] == [False, True]
    assert not changed(doughnut, "doughnut=false").doughnut


@pytest.mark.parametrize("query", ["doughnut=maybe", "doughnut"])
def test_bad_doughnut_queries_are_rejected(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(sample_pie_state(), query)


def test_other_kinds_have_no_doughnut_option() -> None:
    with pytest.raises(ValueError, match="no doughnut option"):
        changed(sample_state(), "doughnut=true")


def test_the_other_new_kinds_have_no_variants() -> None:
    assert variants(sample_scatter_state()) == ()
    assert variants(sample_butterfly_state()) == ()


def test_a_butterfly_chart_sorts() -> None:
    state = sample_butterfly_state()
    assert [s.current for s in sort_options(state)] == [True, False, False]
    toggle = sort_toggle(state)
    assert toggle is not None
    assert toggle.command == "ChangeChart?sort=descending"
    assert changed(state, "sort=ascending").sort == "ascending"


def test_pie_and_scatter_charts_offer_no_sort() -> None:
    for state in (sample_pie_state(), sample_scatter_state()):
        assert sort_options(state) == ()
        assert sort_toggle(state) is None


# --- format ------------------------------------------------------------------------------------


def test_which_new_kinds_have_which_format_option() -> None:
    pie, scatter, butterfly = sample_pie_state(), sample_scatter_state(), sample_butterfly_state()
    assert [supports(pie, o) for o in ("axis", "gridlines", "series_names")] == [False, False, True]
    assert [supports(scatter, o) for o in ("axis", "gridlines", "series_names")] == [
        False,
        True,
        False,
    ]
    assert [supports(butterfly, o) for o in ("axis", "gridlines", "series_names")] == [
        True,
        True,
        False,
    ]


def test_a_scatter_chart_offers_gridlines_without_an_axis_switch() -> None:
    commands = [s.command for s in format_options(sample_scatter_state())]
    assert commands == ["ChangeFormat?gridlines=true"]
    with pytest.raises(ValueError, match="no axis option"):
        settled(sample_scatter_state(), Format(), "axis=true")


def test_a_butterfly_chart_offers_gridlines_only_with_its_axis() -> None:
    state = sample_butterfly_state()
    assert [s.command for s in format_options(state)] == ["ChangeFormat?axis=true"]
    shown = replace(state, format=Format(axis=True))
    assert [s.command for s in format_options(shown)] == [
        "ChangeFormat?axis=false",
        "ChangeFormat?gridlines=true",
    ]


def test_new_charts_start_with_their_series_names() -> None:
    assert default_format("pie", "stacked", "en-US").series_names == "labels"
    assert default_format("scatter", "stacked", "en-US").series_names == "none"
    assert default_format("butterfly", "stacked", "en-US").series_names == "none"


# --- annotations -------------------------------------------------------------------------------


def test_a_scatter_chart_takes_value_lines_only() -> None:
    assert notes.SUPPORTED["scatter"] == {"value_line"}
    assert "pie" not in notes.SUPPORTED
    assert "butterfly" not in notes.SUPPORTED


def test_a_scatter_value_line_averages_the_y_values() -> None:
    state = sample_scatter_state()
    ys = [30, 42, 38, 55, 18, 25, 33, 48]
    assert value_line.average_for(state) == pytest.approx(sum(ys) / len(ys))
    data = notes.measured(state)
    assert len(data.categories) == 8
    assert notes.drawable(Annotation("value_line", 0, 0), data, "scatter")


def test_annotations_are_not_drawn_on_pie_and_butterfly_charts() -> None:
    line = Annotation("value_line", 0, 0, value=5.0)
    for state in (sample_pie_state(), sample_butterfly_state()):
        assert not notes.drawable(line, notes.measured(state), state.kind)


# --- menu and panel ----------------------------------------------------------------------------


def test_the_pie_menu_offers_the_doughnut_switch() -> None:
    commands = [
        item.command for item in chart_menu(sample_pie_state(), "en-US").children if item.command
    ]
    assert PROTOCOL + "ChangeChart?doughnut=true" in commands
    assert PROTOCOL + "ChangeChart?doughnut=false" not in commands


def test_the_scatter_colour_menu_lists_the_groups() -> None:
    menu = chart_menu(sample_scatter_state(), "en-US")
    colours = next(item for item in menu.children if item.title == "Series colour")
    assert [item.title for item in colours.children] == ["Group 1", "Group 2"]


def test_a_scatter_menu_offers_the_value_line_but_no_arrows() -> None:
    all_titles = titles(sample_scatter_state())
    assert "Add value line..." in all_titles or any("value line" in t.lower() for t in all_titles)
    assert not any("ifference" in t for t in all_titles)


def test_the_panel_names_the_kind_and_its_variant() -> None:
    pie = content(sample_pie_state(), True, "en-US")
    assert pie.status == "Pie chart, 2 categories"
    assert content(replace(sample_pie_state(), doughnut=True), True, "en-US").status.startswith(
        "Doughnut chart"
    )
    assert content(sample_scatter_state(), True, "de-DE").status.startswith("Streudiagramm")
    assert content(sample_butterfly_state(), True, "en-US").status.startswith("Butterfly chart")


def test_the_panel_tells_when_a_scatter_chart_has_bubbles() -> None:
    state = sample_scatter_state()
    sized = replace(
        state,
        cells=state.cells,
        values=tuple(
            row if r == 0 else (*row[:3], 5.0, *row[4:]) for r, row in enumerate(state.values)
        ),
    )
    assert content(sized, True, "en-US").status.startswith("Bubble chart")


def test_the_panel_says_that_a_butterfly_chart_ignores_further_series() -> None:
    state = sample_butterfly_state()
    wide = replace(
        state,
        cells=(*state.cells, ("Other", *("1",) * 5)),
        values=(*state.values, (None, *(1.0,) * 5)),
    )
    assert "Only the first two series" in content(wide, True, "en-US").status
    assert "Only the first two" not in content(state, True, "en-US").status


def test_the_panel_offers_the_three_new_chart_types() -> None:
    commands = [b.command for b in content(None, False, "en-US").insert]
    assert commands[-3:] == [
        PROTOCOL + "InsertPieChart",
        PROTOCOL + "InsertScatterChart",
        PROTOCOL + "InsertButterflyChart",
    ]


# --- same scale --------------------------------------------------------------------------------


def test_a_butterfly_chart_can_share_a_scale_with_bar_charts_only() -> None:
    butterfly = sample_butterfly_state()
    bar = replace(sample_state(), kind="bar")
    assert samescale.orientation(butterfly) == "horizontal"
    assert samescale.can_join([butterfly, bar])
    assert not samescale.can_join([butterfly, sample_state()])
    length = samescale.natural_length_per_unit(butterfly, 12000, 7000)
    assert length is not None
    assert length > 0


def test_pie_and_scatter_charts_have_no_scale_to_share() -> None:
    for state in (sample_pie_state(), sample_scatter_state()):
        assert samescale.orientation(state) is None
        assert not samescale.joinable(state)
