import pytest

from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.options import (
    Switch,
    can_draw_lines,
    changed,
    line_query,
    secondary_query,
    sort_options,
    sort_toggle,
    variants,
)


def test_a_column_offers_all_three_variants_with_the_current_one_marked() -> None:
    assert variants(sample_state()) == (
        Switch("menu_stacked", "ChangeChart?grouping=stacked", True),
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


def test_an_area_chart_switches_between_stacked_and_100_percent() -> None:
    area = state_from_table("area", "stacked", [[None, "2024"], ["Sales", 10]])
    assert variants(area) == (
        Switch("menu_stacked", "ChangeChart?grouping=stacked", True),
        Switch("menu_percent", "ChangeChart?percent=true", False),
    )
    percent = changed(area, "percent=true")
    assert percent.percent
    assert variants(percent)[0].current is False
    assert variants(percent)[1].current is True
    assert not changed(percent, "percent=false").percent
    with pytest.raises(ValueError, match="always stacked"):
        changed(area, "grouping=clustered")


def test_only_a_column_that_is_not_100_percent_can_draw_lines() -> None:
    assert can_draw_lines(sample_state())
    assert can_draw_lines(changed(sample_state(), "grouping=clustered"))
    assert not can_draw_lines(changed(sample_state(), "percent=true"))
    assert not can_draw_lines(sample_waterfall_state())


def test_line_and_secondary_queries_carry_the_series_and_the_flag() -> None:
    assert line_query(0, True) == "ChangeChart?line=0&on=true"
    assert line_query(2, False) == "ChangeChart?line=2&on=false"
    assert secondary_query(1, True) == "ChangeChart?secondary=1&on=true"
    assert secondary_query(1, False) == "ChangeChart?secondary=1&on=false"


def test_a_series_can_be_drawn_as_a_line_and_back() -> None:
    state = changed(sample_state(), "line=1&on=true")
    assert state.lines == (1,)
    assert state.secondary == ()
    assert changed(state, "line=1&on=false").lines == ()
    assert changed(sample_state(), "line=0&on=true").lines == (0,)
    assert changed(sample_state(), "line=2&on=true").lines == (2,)


def test_the_secondary_axis_only_carries_lines() -> None:
    state = changed(sample_state(), "secondary=1&on=true")
    assert state.lines == (1,)
    assert state.secondary == (1,)
    assert changed(state, "secondary=1&on=false").secondary == ()
    assert changed(state, "secondary=1&on=false").lines == (1,)


def test_a_series_that_stops_being_a_line_also_leaves_the_secondary_axis() -> None:
    state = changed(changed(sample_state(), "line=1&on=true"), "secondary=1&on=true")
    back = changed(state, "line=1&on=false")
    assert back.lines == ()
    assert back.secondary == ()


def test_line_series_survive_a_variant_switch_but_not_100_percent() -> None:
    state = changed(sample_state(), "line=0&on=true")
    assert changed(state, "grouping=clustered").lines == (0,)
    percent = changed(state, "percent=true")
    assert percent.lines == ()
    assert percent.secondary == ()


@pytest.mark.parametrize(
    "query",
    [
        "line=0&on=maybe",
        "line=x&on=true",
        "line=-1&on=true",
        "line=3&on=true",
        "line=0&on=true&sort=none",
    ],
)
def test_bad_line_queries_are_rejected(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(sample_state(), query)


@pytest.mark.parametrize("kind", ["waterfall", "mekko", "area"])
def test_other_kinds_reject_line_series(kind: str) -> None:
    state = {
        "waterfall": sample_waterfall_state,
        "mekko": sample_mekko_state,
        "area": lambda: state_from_table("area", "stacked", [[None, "2024"], ["Sales", 10]]),
    }[kind]()
    with pytest.raises(ValueError, match="cannot draw series as lines"):
        changed(state, "line=0&on=true")


def test_a_100_percent_chart_rejects_line_series() -> None:
    with pytest.raises(ValueError, match="100 %"):
        changed(changed(sample_state(), "percent=true"), "line=0&on=true")
