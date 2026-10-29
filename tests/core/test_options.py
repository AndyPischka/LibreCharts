import pytest

from librecharts.core.datasheet import sample_mekko_state, sample_state, sample_waterfall_state
from librecharts.core.options import changed, toggle


def test_a_percent_mekko_switches_to_units() -> None:
    assert toggle(sample_mekko_state()) == ("menu_mekko_units", "ChangeChart?percent=false")


def test_a_units_mekko_switches_to_percent() -> None:
    state = changed(sample_mekko_state(), "percent=false")
    assert toggle(state) == ("menu_mekko_percent", "ChangeChart?percent=true")


@pytest.mark.parametrize("state", [sample_state(), sample_waterfall_state()])
def test_charts_without_options_have_no_switch(state: object) -> None:
    assert toggle(state) is None  # pyright: ignore[reportArgumentType]


def test_changed_applies_the_option() -> None:
    state = sample_mekko_state()
    assert not changed(state, "percent=false").percent
    assert changed(changed(state, "percent=false"), "percent=true").percent
    assert changed(state, "percent=false").cells == state.cells


def test_the_last_value_wins() -> None:
    assert not changed(sample_mekko_state(), "percent=true&percent=false").percent


@pytest.mark.parametrize(
    "query", ["", "percent", "percent=maybe", "percent=", "colour=red", "percent=true&colour=red"]
)
def test_invalid_queries_are_rejected(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(sample_mekko_state(), query)


def test_a_chart_without_the_option_rejects_it() -> None:
    with pytest.raises(ValueError, match="no percent option"):
        changed(sample_state(), "percent=false")
