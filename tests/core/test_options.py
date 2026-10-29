import pytest

from librecharts.core.datasheet import sample_mekko_state, sample_state, sample_waterfall_state
from librecharts.core.options import (
    Switch,
    changed,
    sort_options,
    sort_toggle,
    variants,
)


def test_a_column_offers_all_three_variants_with_the_current_one_marked() -> None:
    assert variants(sample_state()) == (
        Switch("menu_stacked", "ChangeChart?grouping=stacked&percent=false", True),
        Switch("menu_clustered", "ChangeChart?grouping=clustered", False),
        Switch("menu_percent", "ChangeChart?percent=true", False),
    )


def test_a_clustered_chart_marks_clustered() -> None:
    state = changed(sample_state(), "grouping=clustered")
    assert variants(state)[1].current
    assert not variants(state)[0].current


def test_a_100_percent_chart_marks_the_100_percent_variant() -> None:
    state = changed(sample_state(), "percent=true")
    assert state.grouping == "stacked"
    assert variants(state)[2].current
    assert not variants(state)[0].current


def test_a_percent_mekko_offers_both_variants() -> None:
    assert variants(sample_mekko_state()) == (
        Switch("menu_mekko_percent", "ChangeChart?percent=true", True),
        Switch("menu_mekko_units", "ChangeChart?percent=false", False),
    )


@pytest.mark.parametrize("state", [sample_waterfall_state()])
def test_charts_without_options_have_no_switch(state: object) -> None:
    assert variants(state) == ()  # pyright: ignore[reportArgumentType]
    assert sort_options(state) == ()  # pyright: ignore[reportArgumentType]
    assert sort_toggle(state) is None  # pyright: ignore[reportArgumentType]


def test_sort_options_and_the_cycle() -> None:
    state = sample_state()
    assert [s.command for s in sort_options(state)] == [
        "ChangeChart?sort=none",
        "ChangeChart?sort=descending",
        "ChangeChart?sort=ascending",
    ]
    assert sort_options(state)[0].current
    assert sort_toggle(state) == Switch("menu_sort_descending", "ChangeChart?sort=descending")
    descending = changed(state, "sort=descending")
    assert sort_toggle(descending) == Switch("menu_sort_ascending", "ChangeChart?sort=ascending")
    ascending = changed(descending, "sort=ascending")
    assert sort_toggle(ascending) == Switch("menu_sort_none", "ChangeChart?sort=none")


def test_changed_applies_the_variants() -> None:
    state = sample_state()
    clustered = changed(state, "grouping=clustered")
    assert clustered.grouping == "clustered"
    assert not clustered.percent
    assert changed(clustered, "grouping=stacked").grouping == "stacked"
    percent = changed(state, "percent=true")
    assert percent.percent
    assert percent.grouping == "stacked"
    assert not changed(percent, "percent=false").percent
    assert changed(clustered, "percent=true").grouping == "stacked"


def test_the_mekko_keeps_its_percent_switch() -> None:
    state = sample_mekko_state()
    assert not changed(state, "percent=false").percent
    assert changed(changed(state, "percent=false"), "percent=true").percent
    assert changed(state, "percent=false").cells == state.cells


def test_the_last_value_wins() -> None:
    assert not changed(sample_mekko_state(), "percent=true&percent=false").percent


@pytest.mark.parametrize(
    "query",
    [
        "",
        "percent",
        "percent=maybe",
        "percent=",
        "colour=red",
        "percent=true&colour=red",
        "grouping=stacked&percent=false",
        "sort=sideways",
        "grouping=diagonal",
    ],
)
def test_invalid_queries_are_rejected(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(sample_state(), query)


@pytest.mark.parametrize("kind", ["waterfall", "mekko"])
def test_kinds_without_a_variant_or_sort_reject_it(kind: str) -> None:
    state = sample_waterfall_state() if kind == "waterfall" else sample_mekko_state()
    with pytest.raises(ValueError, match="grouping option"):
        changed(state, "grouping=clustered")
    with pytest.raises(ValueError, match="cannot be sorted"):
        changed(state, "sort=descending")


def test_a_waterfall_rejects_the_percent_option() -> None:
    with pytest.raises(ValueError, match="no percent option"):
        changed(sample_waterfall_state(), "percent=true")
