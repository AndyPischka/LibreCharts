import pytest

from librecharts.core.datasheet import (
    ChartData,
    Series,
    parse,
    sample_state,
    state_from_sheet,
    state_from_table,
)


def test_parses_categories_series_and_values() -> None:
    state = state_from_table(
        "column",
        "stacked",
        [[None, "2024", "2025"], ["Sales", 10, 20], ["Costs", 5.5, 7]],
    )
    assert parse(state) == ChartData(
        categories=("2024", "2025"),
        series=(Series("Sales", (10.0, 20.0)), Series("Costs", (5.5, 7.0))),
    )


def test_empty_cells_inside_the_data_stay_gaps() -> None:
    state = state_from_table("column", "stacked", [[None, "A", "B", "C"], ["S", 1, None, 3]])
    assert parse(state).series[0].values == (1.0, None, 3.0)


def test_text_in_value_cells_counts_as_empty() -> None:
    state = state_from_table("column", "stacked", [[None, "A", "B"], ["S", "n/a", 2]])
    assert parse(state).series[0].values == (None, 2.0)


def test_trailing_empty_rows_and_columns_are_dropped() -> None:
    state = state_from_table(
        "column",
        "stacked",
        [[None, "A", None, None], ["S", 1, None, None], [None, None, None, None]],
    )
    assert parse(state) == ChartData(("A",), (Series("S", (1.0,)),))


def test_unnamed_series_get_a_default_name() -> None:
    state = state_from_table("column", "stacked", [[None, "A"], [None, 1], ["", 2]])
    assert [s.name for s in parse(state).series] == ["Series 1", "Series 2"]


def test_names_are_stripped() -> None:
    state = state_from_table("column", "stacked", [[None, " A "], [" S ", 1]])
    data = parse(state)
    assert data.categories == ("A",)
    assert data.series[0].name == "S"


def test_data_without_a_header_name_is_kept() -> None:
    state = state_from_table("column", "stacked", [[None, None, "B"], ["S", 1, 2]])
    assert parse(state).categories == ("", "B")


def test_too_small_or_empty_tables_yield_no_data() -> None:
    empty = ChartData((), ())
    assert parse(state_from_table("column", "stacked", [])) == empty
    assert parse(state_from_table("column", "stacked", [[None, "A"]])) == empty
    assert parse(state_from_table("column", "stacked", [[None], ["S"]])) == empty
    assert parse(state_from_table("column", "stacked", [[None, None], [None, None]])) == empty


def test_state_from_table_keeps_raw_cell_text() -> None:
    state = state_from_table("column", "clustered", [["x", 10, 2.5, None]])
    assert state.cells == (("x", "10", "2.5", ""),)
    assert state.values == ((None, 10.0, 2.5, None),)
    assert state.grouping == "clustered"


def test_sample_state_is_a_complete_chart() -> None:
    data = parse(sample_state())
    assert data.categories == ("2023", "2024", "2025")
    assert [s.name for s in data.series] == ["Product A", "Product B", "Product C"]
    assert all(None not in s.values for s in data.series)


def test_state_from_sheet_keeps_formulas_and_numeric_results() -> None:
    state = state_from_sheet(
        "column",
        "stacked",
        formulas=[["", "2024"], ["Sales", "=4*5"]],
        results=[["", 2024.0], ["Sales", 20.0]],
    )
    assert state.cells == (("", "2024"), ("Sales", "=4*5"))
    assert state.values == ((None, 2024.0), (None, 20.0))


def test_state_from_sheet_treats_text_errors_and_bools_as_empty() -> None:
    state = state_from_sheet(
        "column",
        "clustered",
        formulas=[["a", "=1/0", "x", "TRUE()"]],
        results=[["a", float("inf"), "x", True]],
    )
    assert state.values == ((None, None, None, None),)
    assert state.grouping == "clustered"


def test_state_from_sheet_rejects_mismatched_grids() -> None:
    with pytest.raises(ValueError, match="same number of rows"):
        state_from_sheet("column", "stacked", formulas=[["1"], ["2"]], results=[[1.0]])
