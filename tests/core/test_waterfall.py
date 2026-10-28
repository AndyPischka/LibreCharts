import pytest

from librecharts.core.datasheet import sample_waterfall_state, state_from_table
from librecharts.core.model import ChartState
from librecharts.core.waterfall import Step, WaterfallData, floor, levels, parse_waterfall


def sheet(*rows: list[str | float | None]) -> ChartState:
    return state_from_table("waterfall", "stacked", list(rows))


def test_steps_add_up_and_totals_show_the_running_total() -> None:
    state = sheet(
        [None, "Start", "Up", "Down", "End"],
        ["Value", 100, 30, -10, None],
        ["Total", "x", None, None, "x"],
    )
    assert parse_waterfall(state) == WaterfallData(
        (
            Step("Start", 0, 100, True, True),
            Step("Up", 100, 130, False, True),
            Step("Down", 130, 120, False, True),
            Step("End", 0, 120, True, True),
        )
    )


def test_a_given_total_replaces_the_running_total_and_continues_from_it() -> None:
    state = sheet(
        [None, "A", "Sub", "B"],
        ["Value", 50, 80, 5],
        ["Total", None, "x", None],
    )
    steps = parse_waterfall(state).steps
    assert steps[1] == Step("Sub", 0, 80, True, True)
    assert steps[2] == Step("B", 80, 85, False, True)


def test_a_gap_changes_nothing_and_has_no_value() -> None:
    state = sheet([None, "A", "Gap", "B"], ["Value", 10, None, 5])
    steps = parse_waterfall(state).steps
    assert steps[1] == Step("Gap", 10, 10, False, False)
    assert steps[2].start == 10


@pytest.mark.parametrize("mark", ["x", "1", "Ja", "yes", "TRUE", "sum"])
def test_marks_that_make_a_total(mark: str) -> None:
    state = sheet([None, "A"], ["Value", 5], ["Total", mark])
    assert parse_waterfall(state).steps[0].is_total


@pytest.mark.parametrize("mark", ["", " ", "0", "false", "No", "nein", "n"])
def test_marks_that_do_not_make_a_total(mark: str) -> None:
    state = sheet([None, "A"], ["Value", 5], ["Total", mark])
    assert not parse_waterfall(state).steps[0].is_total


def test_the_marker_row_is_optional() -> None:
    state = sheet([None, "A", "B"], ["Value", 5, -2])
    assert [s.is_total for s in parse_waterfall(state).steps] == [False, False]


def test_an_empty_total_with_nothing_before_is_zero() -> None:
    state = sheet([None, "T"], ["Value", None], ["Total", "x"])
    assert parse_waterfall(state).steps == (Step("T", 0, 0, True, True),)


def test_trailing_empty_columns_are_dropped_and_names_stripped() -> None:
    state = sheet([None, " A ", None, None], ["Value", 3, None, None], ["Total", None, None, None])
    assert parse_waterfall(state).steps == (Step("A", 0, 3, False, True),)


@pytest.mark.parametrize(
    "table",
    [[], [[None, "A"]], [[None], ["Value"]], [[None, None], ["Value", None]]],
)
def test_too_small_or_empty_sheets_yield_nothing(table: list[list[str | float | None]]) -> None:
    assert parse_waterfall(sheet(*table)) == WaterfallData(())


def test_change_is_the_difference_of_the_ends() -> None:
    assert Step("x", 5, 2, False, True).change == -3


def test_sample_waterfall_ends_with_the_computed_total() -> None:
    steps = parse_waterfall(sample_waterfall_state()).steps
    assert steps[0].name == "Start"
    assert steps[-1].is_total
    assert steps[-1].end == 110


def test_levels_are_what_the_columns_end_at() -> None:
    data = WaterfallData(
        (
            Step("Start", 0, 100, True, True),
            Step("Down", 100, 70, False, True),
            Step("Gap", 70, 70, False, False),
            Step("End", 0, 70, True, True),
        )
    )
    measured = levels(data)
    assert measured.categories == ("Start", "Down", "Gap", "End")
    assert [s.values for s in measured.series] == [(100, 70, 70, 70)]


def test_floor_is_the_lowest_level_a_step_touches() -> None:
    data = WaterfallData(
        (
            Step("Start", 0, 100, True, True),
            Step("Down", 100, 70, False, True),
            Step("Up", 70, 90, False, True),
            Step("End", 0, 90, True, True),
        )
    )
    assert floor(data) == 70


def test_floor_is_zero_without_steps() -> None:
    assert floor(WaterfallData((Step("Only", 0, 50, True, True),))) == 0
    assert floor(WaterfallData(())) == 0
