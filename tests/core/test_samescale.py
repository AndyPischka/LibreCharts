from dataclasses import replace

from librecharts.core import samescale
from librecharts.core.datasheet import (
    sample_area_state,
    sample_line_state,
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)

WIDTH, HEIGHT = 12000.0, 7000.0


def test_orientation_follows_the_value_axis() -> None:
    assert samescale.orientation(sample_state()) == "vertical"
    assert samescale.orientation(replace(sample_state(), kind="bar")) == "horizontal"
    assert samescale.orientation(sample_line_state()) == "vertical"
    assert samescale.orientation(sample_area_state()) == "vertical"
    assert samescale.orientation(sample_waterfall_state()) == "vertical"
    assert samescale.orientation(replace(sample_mekko_state(), percent=False)) == "vertical"


def test_percent_charts_have_no_comparable_scale() -> None:
    assert samescale.orientation(sample_mekko_state()) is None
    assert samescale.orientation(replace(sample_state(), percent=True)) is None
    assert samescale.orientation(replace(sample_area_state(), percent=True)) is None
    assert not samescale.joinable(sample_mekko_state())


def test_charts_of_one_orientation_can_join() -> None:
    assert samescale.can_join([sample_state(), sample_line_state(), sample_area_state()])
    assert samescale.can_join([replace(sample_state(), kind="bar")])
    assert not samescale.can_join([sample_state(), replace(sample_state(), kind="bar")])
    assert not samescale.can_join([sample_state(), sample_mekko_state()])
    assert not samescale.can_join([])


def test_every_kind_has_a_natural_length_per_unit() -> None:
    for state in (
        sample_state(),
        replace(sample_state(), kind="bar"),
        sample_line_state(),
        sample_area_state(),
        sample_waterfall_state(),
        replace(sample_mekko_state(), percent=False),
    ):
        length = samescale.natural_length_per_unit(state, WIDTH, HEIGHT)
        assert length is not None
        assert length > 0


def test_a_percent_chart_has_no_natural_length() -> None:
    assert samescale.natural_length_per_unit(sample_mekko_state(), WIDTH, HEIGHT) is None
    assert (
        samescale.natural_length_per_unit(replace(sample_state(), percent=True), WIDTH, HEIGHT)
        is None
    )


def test_a_group_uses_the_smallest_natural_length() -> None:
    tall = sample_state()
    short = sample_line_state()
    tall_length = samescale.natural_length_per_unit(tall, WIDTH, HEIGHT)
    short_length = samescale.natural_length_per_unit(short, WIDTH, HEIGHT // 2)
    assert tall_length is not None
    assert short_length is not None
    assert samescale.common_length_per_unit(
        [(tall, WIDTH, HEIGHT), (short, WIDTH, HEIGHT / 2)]
    ) == min(tall_length, short_length)


def test_an_empty_or_incompatible_group_has_no_common_length() -> None:
    assert samescale.common_length_per_unit([]) is None
    assert (
        samescale.common_length_per_unit(
            [(sample_state(), WIDTH, HEIGHT), (sample_mekko_state(), WIDTH, HEIGHT)]
        )
        is None
    )


def test_charts_too_small_to_lay_out_are_skipped() -> None:
    small = state_from_table("column", "stacked", [[None, "2024"], ["Sales", 10]])
    assert samescale.natural_length_per_unit(small, 10.0, 10.0) is None
    other = sample_state()
    assert samescale.common_length_per_unit([(small, 10.0, 10.0), (other, WIDTH, HEIGHT)]) == (
        samescale.natural_length_per_unit(other, WIDTH, HEIGHT)
    )
