from librecharts.core.datasheet import sample_scatter_state, state_from_table
from librecharts.core.model import ChartState
from librecharts.core.scatter import Point, levels, parse_scatter


def scatter(*rows: tuple[object, ...]) -> ChartState:
    table: list[list[object]] = [["Label", "X", "Y", "Size", "Group"], *[list(r) for r in rows]]
    return state_from_table("scatter", "stacked", table)  # pyright: ignore[reportArgumentType]


def test_the_sample_has_two_named_groups_and_no_bubbles() -> None:
    data = parse_scatter(sample_scatter_state())
    assert len(data.points) == 8
    assert data.groups == ("Group 1", "Group 2")
    assert not data.bubbles
    assert data.points[0] == Point("Alpha", 12, 30, None, 0)
    assert data.points[-1].group == 1


def test_rows_without_a_number_in_x_or_y_are_skipped() -> None:
    data = parse_scatter(
        scatter(
            ("A", 1, 2, None, None),
            ("B", None, 2, None, None),
            ("C", 3, None, None, None),
            ("D", "text", 4, None, None),
            ("E", 5, 6, None, None),
        )
    )
    assert [p.label for p in data.points] == ["A", "E"]


def test_a_positive_size_makes_a_bubble_chart() -> None:
    data = parse_scatter(scatter(("A", 1, 2, 10, None), ("B", 3, 4, None, None)))
    assert data.bubbles
    assert [p.size for p in data.points] == [10, None]


def test_sizes_of_zero_or_below_count_as_empty() -> None:
    data = parse_scatter(scatter(("A", 1, 2, 0, None), ("B", 3, 4, -5, None)))
    assert [p.size for p in data.points] == [None, None]
    assert not data.bubbles


def test_groups_are_numbered_by_first_appearance() -> None:
    data = parse_scatter(
        scatter(("A", 1, 2, None, "red"), ("B", 3, 4, None, "blue"), ("C", 5, 6, None, "red"))
    )
    assert data.groups == ("red", "blue")
    assert [p.group for p in data.points] == [0, 1, 0]


def test_without_group_and_size_columns_all_points_share_one_unnamed_group() -> None:
    state = state_from_table("scatter", "stacked", [["", "X", "Y"], ["A", 1, 2], ["B", 3, 4]])
    data = parse_scatter(state)
    assert data.groups == ("",)
    assert [p.size for p in data.points] == [None, None]


def test_a_sheet_without_data_has_no_points() -> None:
    assert parse_scatter(state_from_table("scatter", "stacked", [["", "X", "Y"]])).points == ()
    assert parse_scatter(state_from_table("scatter", "stacked", [["", "X"], ["A", 1]])).points == ()


def test_levels_offer_the_y_values_to_annotations() -> None:
    data = levels(parse_scatter(scatter(("A", 1, 2, None, None), ("B", 3, 8, None, None))))
    assert data.categories == ("A", "B")
    assert data.series[0].values == (2, 8)
