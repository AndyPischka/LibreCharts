from dataclasses import replace
from itertools import pairwise

import pytest

from librecharts.core.datasheet import ChartData, Series, sample_mekko_state, state_from_table
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.mekko import (
    CATEGORY_BAND,
    LABEL_HEIGHT,
    MIN_OUTSIDE_LABEL_WIDTH,
    RIGHT_BAND,
    TOP_BAND,
    WIDTH_BAND,
    layout_mekko,
)
from librecharts.core.mekko import MekkoData, has_width_row, parse_mekko
from librecharts.core.model import ChartState
from librecharts.core.primitives import Line, Rect, Text


def sheet(*rows: list[str | float | None]) -> ChartState:
    return state_from_table("mekko", "stacked", list(rows))


def mekko(
    *series: tuple[str, tuple[float | None, ...]],
    categories: tuple[str, ...],
    widths: tuple[float, ...],
) -> MekkoData:
    return MekkoData(ChartData(categories, tuple(Series(n, v) for n, v in series)), widths)


# --- data sheet rules -------------------------------------------------------------------------


def test_widths_default_to_the_column_sums() -> None:
    parsed = parse_mekko(sheet([None, "A", "B"], ["S1", 30, 10], ["S2", 10, 5]))
    assert parsed.widths == (40, 15)
    assert [s.name for s in parsed.data.series] == ["S1", "S2"]


@pytest.mark.parametrize("name", ["Width", "width", " Breite "])
def test_a_width_row_sets_the_widths_and_is_not_a_series(name: str) -> None:
    state = sheet([None, "A", "B"], [name, 7, None], ["S1", 30, 10], ["S2", 10, 5])
    assert has_width_row(state)
    parsed = parse_mekko(state)
    assert parsed.widths == (7, 15)  # an empty width cell falls back to the column sum
    assert [s.name for s in parsed.data.series] == ["S1", "S2"]


def test_a_width_row_must_follow_the_names_directly() -> None:
    state = sheet([None, "A"], ["S1", 3], ["Width", 9])
    assert not has_width_row(state)
    assert [s.name for s in parse_mekko(state).data.series] == ["S1", "Width"]


def test_negative_and_text_values_count_as_empty() -> None:
    parsed = parse_mekko(sheet([None, "A"], ["S1", -5], ["S2", "n/a"], ["S3", 4]))
    assert [s.values for s in parsed.data.series] == [(None,), (None,), (4.0,)]
    assert parsed.widths == (4,)


def test_non_positive_given_widths_fall_back_to_the_sum() -> None:
    parsed = parse_mekko(sheet([None, "A", "B"], ["Width", 0, -3], ["S1", 2, 5]))
    assert parsed.widths == (2, 5)


def test_sample_has_four_markets_and_three_products() -> None:
    parsed = parse_mekko(sample_mekko_state())
    assert parsed.data.categories == ("Europe", "Americas", "Asia", "Other")
    assert len(parsed.data.series) == 3
    assert parsed.widths == (80, 85, 90, 10)


# --- layout -----------------------------------------------------------------------------------


def test_golden_geometry() -> None:
    # plot 8000 x 8200 (bottom at 9000); widths 40/40 -> two columns of 4000 with a 100 gap
    data = mekko(("S1", (30.0, 10.0)), ("S2", (10.0, 30.0)), categories=("A", "B"), widths=(40, 40))
    assert layout_mekko(data, 10600, 10000) == (
        Line(0, 9000, 8100, 9000, "baseline"),
        Rect(0, 2850, 4000, 6150, 0),
        Text(0, 2850, 4000, 6150, "75%", "center", "value"),
        Rect(0, 800, 4000, 2050, 1),
        Text(0, 800, 4000, 2050, "25%", "center", "value"),
        Text(0, 200, 4000, LABEL_HEIGHT, "40", "center", "total"),
        Text(0, 9000, 4000, CATEGORY_BAND, "A", "center", "category"),
        Rect(4100, 6950, 4000, 2050, 0),
        Text(4100, 6950, 4000, 2050, "25%", "center", "value"),
        Rect(4100, 800, 4000, 6150, 1),
        Text(4100, 800, 4000, 6150, "75%", "center", "value"),
        Text(4100, 200, 4000, LABEL_HEIGHT, "40", "center", "total"),
        Text(4100, 9000, 4000, CATEGORY_BAND, "B", "center", "category"),
        Text(8250, 7675, 2350, LABEL_HEIGHT, "S1", "left", "series"),
        Text(8250, 3575, 2350, LABEL_HEIGHT, "S2", "left", "series"),
    )


def test_column_widths_are_proportional_to_the_widths() -> None:
    data = mekko(("S", (1.0, 1.0)), categories=("A", "B"), widths=(10, 30))
    rects = [p for p in layout_mekko(data, 10600, 10000) if isinstance(p, Rect)]
    assert [r.width for r in rects] == [2000, 6000]
    assert rects[1].x == 2000 + 100


def test_every_column_is_full_height() -> None:
    primitives = layout_chart(sample_mekko_state(), 24000, 12000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    for c in range(4):
        column = rects[c * 3 : c * 3 + 3]
        assert sum(r.height for r in column) == pytest.approx(12000 - TOP_BAND - CATEGORY_BAND)


def test_small_segments_and_narrow_columns_get_empty_labels() -> None:
    data = mekko(
        ("S1", (1.0, 5.0)), ("S2", (99.0, 5.0)), categories=("Wide", "Thin"), widths=(100, 1)
    )
    texts = [p for p in layout_mekko(data, 10600, 10000) if isinstance(p, Text)]
    values = [t.text for t in texts if t.role == "value"]
    widths = [t.text for t in texts if t.role == "total"]
    assert values == ["", "99%", "", ""]
    assert widths == ["100", "1"]


def test_outside_labels_of_narrow_columns_get_a_wider_centred_box() -> None:
    data = mekko(("S", (1.0, 1.0, 1.0)), categories=("Wide", "Thin", "End"), widths=(100, 1, 1))
    primitives = layout_mekko(data, 10600, 10000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    names = [p for p in primitives if isinstance(p, Text) and p.role == "category"]
    assert names[0].width == rects[0].width  # wide enough: box = column
    thin, thin_name = rects[1], names[1]
    assert thin_name.width == MIN_OUTSIDE_LABEL_WIDTH
    assert thin_name.x + thin_name.width / 2 == pytest.approx(thin.x + thin.width / 2)
    assert names[2].x + names[2].width <= 10600  # clamped at the right edge


def test_empty_cells_give_zero_height_segments_without_labels() -> None:
    data = mekko(("S1", (None,)), ("S2", (4.0,)), categories=("A",), widths=(4,))
    primitives = layout_mekko(data, 10600, 10000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    assert rects[0].height == 0
    values = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert values == ["", "100%"]


def test_all_zero_data_still_lays_out() -> None:
    data = mekko(("S", (None, None)), categories=("A", "B"), widths=(0, 0))
    assert layout_mekko(data, 10600, 10000)


def test_series_names_sit_right_of_the_plot() -> None:
    primitives = layout_chart(sample_mekko_state(), 24000, 12000)
    names = [p for p in primitives if isinstance(p, Text) and p.role == "series"]
    assert [n.text for n in names] == ["Product A", "Product B", "Product C"]
    assert all(n.x + n.width <= 24000 + 1e-9 for n in names)
    assert all(n.x >= 24000 - RIGHT_BAND for n in names)


def test_all_geometry_stays_inside_the_box() -> None:
    for p in layout_chart(sample_mekko_state(), 24000, 12000):
        if isinstance(p, Rect | Text):
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9


def test_structure_does_not_depend_on_size() -> None:
    state = sheet(
        [None, "A", "B", "C"], ["Width", 5, None, 1], ["S1", 1, -2, None], ["S2", 300, 5, 0]
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", "")) for p in layout_chart(state, width, height)
        ]

    assert shape(4000, 3000) == shape(30000, 20000) == shape(3200, 2500)


def test_empty_data_yields_nothing() -> None:
    assert layout_mekko(MekkoData(ChartData((), ()), ()), 10600, 10000) == ()


@pytest.mark.parametrize(
    ("width", "height"),
    [(RIGHT_BAND, 10000), (RIGHT_BAND + 100, 10000), (10600, TOP_BAND + CATEGORY_BAND)],
)
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    data = mekko(("S", (1.0, 1.0)), categories=("A", "B"), widths=(1, 1))
    with pytest.raises(ValueError, match="too small"):
        layout_mekko(data, width, height)


# --- units variant ----------------------------------------------------------------------------


def units_state(*rows: list[str | float | None]) -> ChartState:
    return replace(sheet(*rows), percent=False)


def test_units_golden_geometry() -> None:
    # plot 8000 x 7600 (bottom at 8400); sums 40 and 40 fill the scale 0..40
    data = mekko(("S1", (30.0, 10.0)), ("S2", (10.0, 30.0)), categories=("A", "B"), widths=(40, 40))
    assert layout_mekko(data, 10600, 10000, percent=False) == (
        Line(0, 8400, 8100, 8400, "baseline"),
        Rect(0, 2700, 4000, 5700, 0),
        Text(0, 2700, 4000, 5700, "30", "center", "value"),
        Rect(0, 800, 4000, 1900, 1),
        Text(0, 800, 4000, 1900, "10", "center", "value"),
        Text(0, 200, 4000, LABEL_HEIGHT, "40", "center", "total"),
        Text(0, 8400, 4000, CATEGORY_BAND, "A", "center", "category"),
        Text(0, 9400, 4000, LABEL_HEIGHT, "40", "center", "value"),
        Rect(4100, 6500, 4000, 1900, 0),
        Text(4100, 6500, 4000, 1900, "10", "center", "value"),
        Rect(4100, 800, 4000, 5700, 1),
        Text(4100, 800, 4000, 5700, "30", "center", "value"),
        Text(4100, 200, 4000, LABEL_HEIGHT, "40", "center", "total"),
        Text(4100, 8400, 4000, CATEGORY_BAND, "B", "center", "category"),
        Text(4100, 9400, 4000, LABEL_HEIGHT, "40", "center", "value"),
        Text(8250, 7150, 2350, LABEL_HEIGHT, "S1", "left", "series"),
        Text(8250, 3350, 2350, LABEL_HEIGHT, "S2", "left", "series"),
    )


def test_units_column_heights_follow_the_sums() -> None:
    data = mekko(("S1", (10.0, 20.0)), ("S2", (10.0, 20.0)), categories=("A", "B"), widths=(1, 1))
    rects = [p for p in layout_mekko(data, 10600, 10000, percent=False) if isinstance(p, Rect)]
    heights = [rects[0].height + rects[1].height, rects[2].height + rects[3].height]
    assert heights[1] == pytest.approx(2 * heights[0])


def test_units_scale_is_a_nice_value_above_the_tallest_column() -> None:
    # tallest sum 43 -> scale 0..50: that column is 43/50 of the plot height
    data = mekko(("S", (43.0, 10.0)), categories=("A", "B"), widths=(1, 1))
    rects = [p for p in layout_mekko(data, 10600, 10000, percent=False) if isinstance(p, Rect)]
    plot_height = 10000 - TOP_BAND - CATEGORY_BAND - WIDTH_BAND
    assert rects[0].height == pytest.approx(plot_height * 43 / 50)
    assert rects[1].height == pytest.approx(plot_height * 10 / 50)


def test_units_labels_show_values_sums_and_widths() -> None:
    data = mekko(("S", (12.5, 0.0)), categories=("A", "B"), widths=(7, 9))
    texts = [p for p in layout_mekko(data, 10600, 10000, percent=False) if isinstance(p, Text)]
    assert [t.text for t in texts if t.role == "total"] == ["12.5", "0"]
    assert [t.text for t in texts if t.role == "value" and t.height == LABEL_HEIGHT] == ["7", "9"]
    assert [t.text for t in texts if t.role == "value" and t.height != LABEL_HEIGHT] == ["12.5", ""]


def test_units_all_geometry_stays_inside_the_box() -> None:
    state = replace(sample_mekko_state(), percent=False)
    for p in layout_chart(state, 24000, 12000):
        if isinstance(p, Rect | Text):
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9


def test_units_structure_does_not_depend_on_size() -> None:
    state = units_state(
        [None, "A", "B", "C"], ["Width", 5, None, 1], ["S1", 1, -2, None], ["S2", 300, 5, 0]
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", "")) for p in layout_chart(state, width, height)
        ]

    assert shape(4000, 3000) == shape(30000, 20000) == shape(3200, 2500)


def test_units_all_zero_data_still_lays_out() -> None:
    data = mekko(("S", (None, None)), categories=("A", "B"), widths=(0, 0))
    assert layout_mekko(data, 10600, 10000, percent=False)


def test_units_needs_room_for_the_width_band() -> None:
    data = mekko(("S", (1.0, 1.0)), categories=("A", "B"), widths=(1, 1))
    assert layout_mekko(data, 10600, TOP_BAND + CATEGORY_BAND + 100)  # percent still fits
    with pytest.raises(ValueError, match="too small"):
        layout_mekko(data, 10600, TOP_BAND + CATEGORY_BAND + 100, percent=False)


def test_the_state_selects_the_variant() -> None:
    percent = layout_chart(sample_mekko_state(), 24000, 12000)
    units = layout_chart(replace(sample_mekko_state(), percent=False), 24000, 12000)
    assert percent != units
    assert any(isinstance(p, Text) and p.text.endswith("%") for p in percent)
    assert not any(isinstance(p, Text) and p.text.endswith("%") for p in units)


def test_a_new_mekko_is_a_percent_mekko() -> None:
    assert sample_mekko_state().percent


def test_only_a_mekko_or_a_stacked_column_or_bar_can_be_a_percent_chart() -> None:
    with pytest.raises(ValueError, match="percent"):
        state_from_table("waterfall", "stacked", [[None, "A"], ["S", 1]], percent=True)
    with pytest.raises(ValueError, match="percent"):
        state_from_table("column", "clustered", [[None, "A"], ["S", 1]], percent=True)
    assert state_from_table("column", "stacked", [[None, "A"], ["S", 1]], percent=True).percent


# --- series names -----------------------------------------------------------------------------


def test_series_names_of_thin_segments_do_not_overlap() -> None:
    for percent in (True, False):
        data = mekko(
            ("A", (50.0, 1.0)),
            ("B", (50.0, 1.0)),
            ("C", (50.0, 1.0)),
            categories=("Big", "Thin"),
            widths=(10, 1),
        )
        names = [
            p
            for p in layout_mekko(data, 10600, 10000, percent=percent)
            if isinstance(p, Text) and p.role == "series"
        ]
        assert [n.text for n in names] == ["A", "B", "C"]
        for lower, upper in pairwise(names):
            assert upper.y + upper.height <= lower.y + 1e-9
        assert min(n.y for n in names) >= 0


def test_series_names_keep_their_place_when_there_is_room() -> None:
    data = mekko(("A", (30.0, 10.0)), ("B", (10.0, 30.0)), categories=("X", "Y"), widths=(40, 40))
    names = [
        p for p in layout_mekko(data, 10600, 10000) if isinstance(p, Text) and p.role == "series"
    ]
    assert [n.y for n in names] == [7675, 3575]


def test_a_stack_of_names_reaching_the_top_moves_down() -> None:
    # 12 series in a plot only 2200 high: the names need more room than the plot has
    series = tuple((f"S{i}", (1.0, 1.0)) for i in range(12))
    data = mekko(*series, categories=("A", "B"), widths=(1, 1))
    names = [
        p for p in layout_mekko(data, 10600, 4000) if isinstance(p, Text) and p.role == "series"
    ]
    assert min(n.y for n in names) == 0
