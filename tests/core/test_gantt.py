from datetime import date

import pytest

from librecharts.core.datasheet import Cell, sample_gantt_state, state_from_table
from librecharts.core.gantt import EPOCH, parse_gantt, serial, starts, to_date
from librecharts.core.model import ChartState

HEADER = ["Activity", "Start", "End", "Remark", "Phase"]


def day(month: int, number: int, year: int = 2026) -> int:
    return serial(date(year, month, number))


def gantt(*rows: list[Cell]) -> ChartState:
    return state_from_table("gantt", "stacked", [HEADER, *rows])


def test_serial_numbers_count_days_from_calcs_null_date() -> None:
    assert to_date(0) == EPOCH == date(1899, 12, 30)
    assert to_date(46022) == date(2025, 12, 31)
    assert serial(date(2025, 12, 31)) == 46022


def test_the_1900_leap_year_quirk_does_not_apply_to_calc_serials() -> None:
    # Calc counts from 1899-12-30, so there is no 29 February 1900 (Excel's quirk) to skip.
    assert to_date(60) == date(1900, 2, 28)
    assert to_date(61) == date(1900, 3, 1)


def test_the_time_of_day_is_ignored() -> None:
    assert to_date(46022.75) == date(2025, 12, 31)


@pytest.mark.parametrize("value", [-1e9, 1e9, -693_594.0, 3e6])
def test_dates_outside_the_supported_years_count_as_empty(value: float) -> None:
    assert to_date(value) is None


def test_row_types_follow_from_the_cells() -> None:
    data = parse_gantt(
        gantt(
            ["Phase 1", day(1, 5), day(2, 27), None, "x"],
            ["Bar", day(1, 5), day(1, 30), "Team A", None],
            ["Milestone", day(2, 27), None, None, None],
            ["Same day", day(3, 1), day(3, 1), None, None],
            ["End only", None, day(3, 3), None, None],
            ["Heading", None, None, None, None],
            ["Marker without dates", None, None, None, "x"],
        )
    )
    assert [(row.label, row.kind) for row in data.rows] == [
        ("Phase 1", "phase"),
        ("Bar", "bar"),
        ("Milestone", "milestone"),
        ("Same day", "milestone"),
        ("End only", "milestone"),
        ("Heading", "heading"),
        ("Marker without dates", "heading"),
    ]
    assert data.rows[1].remark == "Team A"
    assert data.rows[2].end == data.rows[2].start == date(2026, 2, 27)
    assert data.rows[4].start == date(2026, 3, 3)
    assert data.rows[5].start is None
    assert data.phases == ("Phase 1",)


def test_swapped_dates_are_put_in_order() -> None:
    (row,) = parse_gantt(gantt(["Late", day(3, 1), day(2, 1), None, None])).rows
    assert (row.start, row.end) == (date(2026, 2, 1), date(2026, 3, 1))


def test_empty_rows_and_text_in_date_cells_are_skipped() -> None:
    data = parse_gantt(
        gantt(
            ["A", day(1, 5), day(1, 9), None, None],
            [None, None, None, None, None],
            ["B", "soon", None, None, None],
        )
    )
    assert [(row.label, row.kind) for row in data.rows] == [("A", "bar"), ("B", "heading")]


def test_dates_from_formulas_are_read_from_the_values() -> None:
    state = gantt(["A", day(1, 5), day(1, 9), None, None])
    cells = (state.cells[0], ("A", str(day(1, 5)), "=B2+14", "", ""))
    values = (state.values[0], (None, float(day(1, 5)), float(day(1, 19)), None, None))
    (row,) = parse_gantt(ChartState("gantt", "stacked", cells, values)).rows
    assert row.end == date(2026, 1, 19)


def test_short_data_sheets_have_no_remark_or_phase_column() -> None:
    state = state_from_table(
        "gantt", "stacked", [["Activity", "Start", "End"], ["A", day(1, 5), day(1, 9)]]
    )
    (row,) = parse_gantt(state).rows
    assert (row.kind, row.remark) == ("bar", "")


def test_rows_take_the_colour_of_the_phase_above_them() -> None:
    data = parse_gantt(sample_gantt_state())
    assert [(row.label, row.color) for row in data.rows] == [
        ("Concept", 0),
        ("Requirements", 0),
        ("Design", 0),
        ("Design approved", 0),
        ("Implementation", 1),
        ("Development", 1),
        ("Testing", 1),
        ("Rollout", 1),
        ("Go-live", 1),
    ]
    assert data.phases == ("Concept", "Implementation")


def test_sorting_by_start_keeps_phases_and_headings_in_place() -> None:
    data = parse_gantt(
        gantt(
            ["C", day(3, 1), day(3, 9), None, None],
            ["A", day(1, 1), day(1, 9), None, None],
            ["Phase", day(1, 1), day(6, 1), None, "x"],
            ["E", day(5, 1), None, None, None],
            ["D", day(2, 1), day(2, 9), None, None],
            ["Heading", None, None, None, None],
            ["G", day(4, 1), day(4, 9), None, None],
            ["F", day(4, 1), day(4, 2), None, None],
        ),
        "ascending",
    )
    assert [row.label for row in data.rows] == ["A", "C", "Phase", "D", "E", "Heading", "G", "F"]


def test_an_empty_data_sheet_has_no_rows() -> None:
    assert parse_gantt(ChartState("gantt", "stacked", (), ())).rows == ()
    assert parse_gantt(gantt()).dated == ()


def test_annotations_measure_the_start_dates() -> None:
    data = starts(parse_gantt(gantt(["A", day(1, 5), None, None, None], ["H", None, None, "", ""])))
    assert data.categories == ("A", "H")
    assert data.series[0].values == (float(day(1, 5)), None)


def test_the_sample_has_two_phases_five_activities_and_two_milestones() -> None:
    kinds = [row.kind for row in parse_gantt(sample_gantt_state()).rows]
    assert (kinds.count("phase"), kinds.count("bar"), kinds.count("milestone")) == (2, 5, 2)
