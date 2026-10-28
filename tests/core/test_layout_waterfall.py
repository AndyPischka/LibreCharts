import pytest

from librecharts.core.datasheet import sample_waterfall_state, state_from_table
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.waterfall import (
    CATEGORY_BAND,
    LABEL_HEIGHT,
    TOP_BAND,
    layout_waterfall,
)
from librecharts.core.primitives import Line, Rect, Text
from librecharts.core.waterfall import Step, WaterfallData, parse_waterfall


def test_golden_geometry() -> None:
    # levels 0..100; the fall reserves 600 below the plot: y(100)=800, y(60)=3840, y(0)=8400
    data = WaterfallData(
        (
            Step("A", 0, 100, True, True),
            Step("B", 100, 60, False, True),
            Step("C", 0, 60, True, True),
        )
    )
    assert layout_waterfall(data, 3000, 10000) == (
        Line(0, 8400, 3000, 8400, "baseline"),
        Rect(150, 800, 700, 7600, 0),
        Text(150, 200, 700, LABEL_HEIGHT, "100", "center", "value"),
        Line(850, 800, 1150, 800, "connector"),
        Text(0, 9000, 1000, CATEGORY_BAND, "A", "center", "category"),
        Rect(1150, 800, 700, 3040, 2),
        Text(1150, 3840, 700, LABEL_HEIGHT, "-40", "center", "value"),
        Line(1850, 3840, 2150, 3840, "connector"),
        Text(1000, 9000, 1000, CATEGORY_BAND, "B", "center", "category"),
        Rect(2150, 3840, 700, 4560, 0),
        Text(2150, 3240, 700, LABEL_HEIGHT, "60", "center", "value"),
        Text(2000, 9000, 1000, CATEGORY_BAND, "C", "center", "category"),
    )


def test_rises_are_signed_and_use_their_own_colour_index() -> None:
    data = WaterfallData((Step("A", 0, 10, True, True), Step("B", 10, 15, False, True)))
    primitives = layout_waterfall(data, 2000, 10000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    assert [r.series for r in rects] == [0, 1]
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["10", "+5"]


def test_a_gap_has_an_empty_label_and_no_height() -> None:
    data = WaterfallData((Step("A", 0, 10, True, True), Step("Gap", 10, 10, False, False)))
    primitives = layout_waterfall(data, 2000, 10000)
    gap = [p for p in primitives if isinstance(p, Rect)][1]
    assert gap.height == 0
    labels = [p.text for p in primitives if isinstance(p, Text) and p.role == "value"]
    assert labels == ["10", ""]


def test_negative_levels_hang_below_the_baseline() -> None:
    data = WaterfallData((Step("A", 0, -20, True, True),))
    primitives = layout_waterfall(data, 1000, 10000)
    baseline = next(p for p in primitives if isinstance(p, Line))
    rect = next(p for p in primitives if isinstance(p, Rect))
    label = next(p for p in primitives if isinstance(p, Text) and p.role == "value")
    assert rect.y == pytest.approx(baseline.y1)
    assert label.y == pytest.approx(rect.y + rect.height)
    category = next(p for p in primitives if isinstance(p, Text) and p.role == "category")
    assert label.y + label.height <= category.y + 1e-9


def test_connectors_join_the_end_of_a_column_to_the_start_of_the_next() -> None:
    primitives = layout_chart(sample_waterfall_state(), 24000, 12000)
    rects = [p for p in primitives if isinstance(p, Rect)]
    connectors = [p for p in primitives if isinstance(p, Line) and p.role == "connector"]
    assert len(connectors) == len(rects) - 1
    for rect, nxt, line in zip(rects, rects[1:], connectors, strict=False):
        assert line.x1 == pytest.approx(rect.x + rect.width)
        assert line.x2 == pytest.approx(nxt.x)
        assert line.y1 == line.y2


def test_all_geometry_stays_inside_the_box() -> None:
    for p in layout_chart(sample_waterfall_state(), 24000, 12000):
        if isinstance(p, Rect | Text):
            assert p.x >= 0
            assert p.x + p.width <= 24000 + 1e-9
            assert p.y >= 0
            assert p.y + p.height <= 12000 + 1e-9


def test_structure_does_not_depend_on_size() -> None:
    state = state_from_table(
        "waterfall",
        "stacked",
        [
            [None, "A", "B", "C", "D"],
            ["Value", 100, -300, None, 7],
            ["Total", "x", None, None, "x"],
        ],
    )

    def shape(width: float, height: float) -> list[tuple[str, str]]:
        return [
            (type(p).__name__, getattr(p, "role", "")) for p in layout_chart(state, width, height)
        ]

    assert shape(4000, 3000) == shape(30000, 20000) == shape(900, 2500)


def test_empty_data_yields_nothing() -> None:
    assert layout_waterfall(WaterfallData(()), 1000, 5000) == ()


def test_all_zero_data_still_lays_out() -> None:
    assert layout_waterfall(WaterfallData((Step("A", 0, 0, True, True),)), 1000, 5000)


@pytest.mark.parametrize(
    ("width", "height"), [(0, 5000), (-1, 5000), (1000, TOP_BAND + CATEGORY_BAND)]
)
def test_too_small_area_is_rejected(width: float, height: float) -> None:
    data = WaterfallData((Step("A", 0, 1, True, True),))
    with pytest.raises(ValueError, match="too small"):
        layout_waterfall(data, width, height)


def test_falls_need_extra_room_below() -> None:
    rise = WaterfallData((Step("A", 0, 5, False, True),))
    fall = WaterfallData((Step("A", 0, -5, False, True),))
    height = TOP_BAND + CATEGORY_BAND + 100
    assert layout_waterfall(rise, 1000, height)
    with pytest.raises(ValueError, match="too small"):
        layout_waterfall(fall, 1000, height)


def test_layout_chart_picks_the_waterfall_layout() -> None:
    state = sample_waterfall_state()
    assert layout_chart(state, 24000, 12000) == layout_waterfall(
        parse_waterfall(state), 24000, 12000
    )
