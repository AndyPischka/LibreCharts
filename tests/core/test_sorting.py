from librecharts.core.datasheet import ChartData, Series
from librecharts.core.model import Annotation
from librecharts.core.sorting import display_index, order, remap, sorted_data


def data(*series: tuple[str, tuple[float | None, ...]]) -> ChartData:
    return ChartData(("A", "B", "C", "D"), tuple(Series(n, v) for n, v in series))


CHART = data(("A", (10.0, 30.0, 20.0, 30.0)), ("B", (5.0, -5.0, None, 10.0)))


def test_unsorted_data_keeps_the_data_sheet_order() -> None:
    assert order(CHART, "stacked", "none") == (0, 1, 2, 3)


def test_stacked_charts_sort_by_the_column_sum_and_keep_ties_stable() -> None:
    assert order(CHART, "stacked", "descending") == (3, 1, 2, 0)
    assert order(CHART, "stacked", "ascending") == (0, 2, 1, 3)


def test_clustered_charts_sort_by_the_first_series() -> None:
    assert order(CHART, "clustered", "descending") == (1, 3, 2, 0)
    assert order(CHART, "clustered", "ascending") == (0, 2, 1, 3)


def test_empty_categories_go_last_in_both_directions() -> None:
    chart = data(("A", (None, 5.0, None, 1.0)), ("B", (None, 2.0, None, None)))
    assert order(chart, "stacked", "descending") == (1, 3, 0, 2)
    assert order(chart, "stacked", "ascending") == (3, 1, 0, 2)
    clustered = data(("A", (None, 5.0, None, 1.0)))
    assert order(clustered, "clustered", "descending") == (1, 3, 0, 2)
    assert order(clustered, "clustered", "ascending") == (3, 1, 0, 2)


def test_a_single_category_is_never_moved() -> None:
    assert order(ChartData(("A",), (Series("S", (1.0,)),)), "stacked", "ascending") == (0,)


def test_data_without_series_has_no_sort_key() -> None:
    assert order(ChartData(("A", "B"), ()), "clustered", "descending") == (0, 1)


def test_sorted_data_permutes_categories_and_values_together() -> None:
    chart = sorted_data(CHART, (1, 3, 2, 0))
    assert chart.categories == ("B", "D", "C", "A")
    assert chart.series[1].values == (-5.0, 10.0, None, 5.0)


def test_display_index_inverts_the_order() -> None:
    assert display_index((1, 3, 2, 0)) == {1: 0, 3: 1, 2: 2, 0: 3}


def test_annotations_follow_their_category() -> None:
    annotations = (
        Annotation("difference", 0, 1),
        Annotation("axis_break", 0, 0),
        Annotation("difference", 3, 2, style="level"),
    )
    moved = remap(annotations, (1, 3, 2, 0))
    assert moved == (
        Annotation("difference", 3, 0),
        Annotation("axis_break", 0, 0),
        Annotation("difference", 1, 2, style="level"),
    )


def test_an_annotation_pointing_past_the_data_keeps_its_index() -> None:
    moved = remap((Annotation("difference", 0, 9),), (1, 3, 2, 0))
    assert moved[0].start == 3
    assert moved[0].end == 9
