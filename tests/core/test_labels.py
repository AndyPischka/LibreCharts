from dataclasses import replace

import pytest

from librecharts.core import labels
from librecharts.core.datasheet import (
    sample_area_state,
    sample_butterfly_state,
    sample_gantt_state,
    sample_line_state,
    sample_mekko_state,
    sample_pie_state,
    sample_scatter_state,
    sample_state,
    sample_waterfall_state,
)
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.common import LABEL_HEIGHT
from librecharts.core.menu import PROTOCOL
from librecharts.core.model import ChartState, LabelKey, LabelOffset
from librecharts.core.options import changed
from librecharts.core.panel import content
from librecharts.core.primitives import (
    Bubble,
    Line,
    Marker,
    Polygon,
    Polyline,
    Primitive,
    Rect,
    Text,
    bounds,
)

WIDTH, HEIGHT = 24000.0, 12000.0


def boxes(primitives: tuple[Primitive, ...]) -> list[labels.Box]:
    return [bounds(p) for p in primitives]


def keyed_texts(state: ChartState) -> list[Text]:
    return [p for p in layout_chart(state, WIDTH, HEIGHT) if isinstance(p, Text) and p.key]


def named(state: ChartState, key: LabelKey) -> Text:
    return next(t for t in keyed_texts(state) if t.key == key)


VARIANTS: dict[str, ChartState] = {
    "stacked column": sample_state(),
    "clustered column": changed(sample_state(), "grouping=clustered"),
    "100 % column": changed(sample_state(), "percent=true"),
    "column with a line": changed(sample_state(), "line=1&on=true"),
    "stacked bar": replace(sample_state(), kind="bar"),
    "clustered bar": changed(replace(sample_state(), kind="bar"), "grouping=clustered"),
    "100 % bar": changed(replace(sample_state(), kind="bar"), "percent=true"),
    "waterfall": sample_waterfall_state(),
    "percent mekko": sample_mekko_state(),
    "mekko in units": changed(sample_mekko_state(), "percent=false"),
    "line": sample_line_state(),
    "area": sample_area_state(),
    "100 % area": changed(sample_area_state(), "percent=true"),
    "pie": sample_pie_state(),
    "doughnut": changed(sample_pie_state(), "doughnut=true"),
    "scatter": sample_scatter_state(),
    "butterfly": sample_butterfly_state(),
}


@pytest.mark.parametrize("name", VARIANTS)
def test_every_value_label_and_total_has_a_unique_key(name: str) -> None:
    primitives = layout_chart(VARIANTS[name], WIDTH, HEIGHT)
    keys = [p.key for p in primitives if isinstance(p, Text) and p.key]
    assert keys
    assert len(set(keys)) == len(keys)
    assert {k.role for k in keys} <= {"value", "total"}
    # No other text is movable: category, series, axis and annotation texts have no key.
    assert all(
        p.key is None
        for p in primitives
        if isinstance(p, Text) and p.role not in ("value", "total")
    )


def test_totals_are_keyed_apart_from_value_labels() -> None:
    keys = {t.key for t in keyed_texts(sample_state())}
    assert LabelKey("total", 0) in keys
    assert LabelKey("value", 0, 0) in keys


def test_a_gantt_chart_has_no_movable_labels() -> None:
    assert keyed_texts(sample_gantt_state()) == []


def test_mekko_width_labels_are_not_movable() -> None:
    state = changed(sample_mekko_state(), "percent=false")
    widths = [
        p
        for p in layout_chart(state, WIDTH, HEIGHT)
        if isinstance(p, Text) and p.role == "value" and p.key is None
    ]
    assert widths


def test_keys_name_data_sheet_indices_when_the_chart_is_sorted() -> None:
    unsorted = sample_state()
    ordered = changed(unsorted, "sort=descending")
    before = {t.key: t.text for t in keyed_texts(unsorted)}
    after = {t.key: t.text for t in keyed_texts(ordered)}
    assert after == before  # the same label has the same key, wherever it is drawn
    moved_x = {t.key: t.x for t in keyed_texts(ordered)}
    assert moved_x != {t.key: t.x for t in keyed_texts(unsorted)}


def test_keys_follow_the_sort_of_a_bar_and_a_butterfly_chart() -> None:
    for state in (replace(sample_state(), kind="bar"), sample_butterfly_state()):
        ordered = replace(state, sort="ascending")
        assert {t.key: t.text for t in keyed_texts(ordered)} == {
            t.key: t.text for t in keyed_texts(state)
        }


@pytest.mark.parametrize("name", VARIANTS)
def test_offsets_do_not_change_the_primitive_structure(name: str) -> None:
    state = VARIANTS[name]
    first = keyed_texts(state)[0]
    offsets = (LabelOffset(first.key, 500.0, -400.0),) if first.key else ()
    plain = layout_chart(state, WIDTH, HEIGHT)
    placed = layout_chart(replace(state, labels=offsets), WIDTH, HEIGHT)
    assert [type(p) for p in plain] == [type(p) for p in placed]
    assert plain != placed


# --- place ------------------------------------------------------------------------------------


def test_a_moved_label_keeps_its_distance_from_its_place() -> None:
    state = sample_state()
    key = LabelKey("total", 0)
    before = named(state, key)
    after = named(replace(state, labels=(LabelOffset(key, 700.0, -250.0),)), key)
    assert after.x + after.width / 2 == pytest.approx(before.x + before.width / 2 + 700)
    assert after.y + after.height / 2 == pytest.approx(before.y + before.height / 2 - 250)
    assert after.text == before.text


def test_a_moved_label_is_revealed_and_at_least_label_height_high() -> None:
    state = changed(sample_state(), "line=0&on=false")
    state = replace(
        state,
        cells=(("", "A"), ("S1", "1"), ("S2", "1000")),
        values=((None, None), (None, 1.0), (None, 1000.0)),
    )
    flat = LabelKey("value", 0, 0)
    hidden = named(state, flat)
    assert hidden.hidden
    assert hidden.height < LABEL_HEIGHT
    moved = named(replace(state, labels=(LabelOffset(flat, 0.0, -2000.0),)), flat)
    assert not moved.hidden
    assert moved.shown == "1"
    assert moved.height == LABEL_HEIGHT
    assert moved.y + moved.height / 2 == pytest.approx(hidden.y + hidden.height / 2 - 2000)


def test_a_label_moved_out_of_its_segment_loses_the_contrast_fill() -> None:
    state = sample_state()
    key = LabelKey("value", 0, 0)
    inside = named(state, key)
    assert inside.fill == 0
    outside = named(replace(state, labels=(LabelOffset(key, 0.0, -9000.0),)), key)
    assert outside.fill is None


def test_a_label_moved_onto_another_segment_takes_its_fill() -> None:
    state = sample_state()
    segments = [
        p for p in layout_chart(state, WIDTH, HEIGHT) if isinstance(p, Rect) and p.series >= 0
    ]
    first, other = (
        next(s for s in segments if s.series == 0),
        next(
            s
            for s in segments
            if s.series == 1 and s.x == next(r.x for r in segments if r.series == 0)
        ),
    )
    label = named(state, LabelKey("value", 0, 0))
    dy = (other.y + other.height / 2) - (label.y + label.height / 2)
    assert first.series == 0
    moved = named(replace(state, labels=(LabelOffset(label.key, 0.0, dy),)), label.key)  # type: ignore[arg-type]
    assert moved.fill == 1


def test_a_label_moved_onto_an_area_takes_the_fill_of_that_area() -> None:
    state = sample_area_state()
    polygons = [p for p in layout_chart(state, WIDTH, HEIGHT) if isinstance(p, Polygon)]
    assert polygons
    label = keyed_texts(state)[0]
    assert label.fill == label.key.series  # type: ignore[union-attr]
    outside = named(replace(state, labels=(LabelOffset(label.key, 0.0, -20000.0),)), label.key)  # type: ignore[arg-type]
    assert outside.fill is None


def test_offsets_of_labels_that_do_not_exist_are_ignored() -> None:
    state = sample_state()
    stale = replace(state, labels=(LabelOffset(LabelKey("value", 99, 0), 100.0, 100.0),))
    assert layout_chart(stale, WIDTH, HEIGHT) == layout_chart(state, WIDTH, HEIGHT)


def test_offsets_are_absolute_and_not_scaled_with_the_chart() -> None:
    key = LabelKey("total", 0)
    state = replace(sample_state(), labels=(LabelOffset(key, 400.0, 0.0),))
    plain = sample_state()

    def shift(size: tuple[float, float]) -> float:
        moved = next(p for p in layout_chart(state, *size) if isinstance(p, Text) and p.key == key)
        base = next(p for p in layout_chart(plain, *size) if isinstance(p, Text) and p.key == key)
        return moved.x - base.x

    assert shift((24000, 12000)) == pytest.approx(400)
    assert shift((12000, 8000)) == pytest.approx(400)


# --- moved ------------------------------------------------------------------------------------


def laid_out(state: ChartState) -> tuple[Primitive, ...]:
    return layout_chart(state, WIDTH, HEIGHT)


def drag(
    primitives: tuple[Primitive, ...], key: LabelKey, dx: float, dy: float
) -> list[labels.Box]:
    result = boxes(primitives)
    for i, p in enumerate(primitives):
        if isinstance(p, Text) and p.key == key:
            x, y, w, h = result[i]
            result[i] = (x + dx, y + dy, w, h)
    return result


def test_nothing_moved_returns_the_stored_offsets() -> None:
    state = replace(sample_state(), labels=(LabelOffset(LabelKey("total", 0), 300.0, 0.0),))
    primitives = laid_out(state)
    assert labels.moved(primitives, boxes(primitives), state.labels) == state.labels
    assert labels.moved(laid_out(sample_state()), boxes(laid_out(sample_state())), ()) == ()


def test_a_dragged_label_becomes_an_offset() -> None:
    primitives = laid_out(sample_state())
    key = LabelKey("value", 1, 1)
    result = labels.moved(primitives, drag(primitives, key, 640.0, -820.0), ())
    assert result == (LabelOffset(key, 640.0, -820.0),)


def test_a_second_drag_adds_to_the_first() -> None:
    key = LabelKey("total", 1)
    state = replace(sample_state(), labels=(LabelOffset(key, 300.0, -200.0),))
    primitives = laid_out(state)
    result = labels.moved(primitives, drag(primitives, key, 100.0, 50.0), state.labels)
    assert result == (LabelOffset(key, 400.0, -150.0),)


def test_several_dragged_labels_are_all_found() -> None:
    primitives = laid_out(sample_state())
    a, b = LabelKey("total", 0), LabelKey("total", 1)
    boxes_ = drag(primitives, a, 200.0, 0.0)
    for i, p in enumerate(primitives):
        if isinstance(p, Text) and p.key == b:
            x, y, w, h = boxes_[i]
            boxes_[i] = (x, y + 300.0, w, h)
    result = labels.moved(primitives, boxes_, ())
    assert result is not None
    assert {o.key: (o.dx, o.dy) for o in result} == {a: (200.0, 0.0), b: (0.0, 300.0)}


def test_a_label_dragged_back_to_within_a_millimetre_snaps_to_its_place() -> None:
    key = LabelKey("total", 0)
    state = replace(sample_state(), labels=(LabelOffset(key, 400.0, 0.0),))
    primitives = laid_out(state)
    assert labels.moved(primitives, drag(primitives, key, -350.0, 0.0), state.labels) == ()
    assert labels.moved(primitives, drag(primitives, key, -250.0, 0.0), state.labels) != ()


def test_a_resize_is_not_a_label_move() -> None:
    state = sample_state()
    small = layout_chart(state, WIDTH / 2, HEIGHT / 2)
    assert labels.moved(laid_out(state), boxes(small), ()) is None


def test_a_moved_bar_is_not_a_label_move() -> None:
    primitives = laid_out(sample_state())
    result = boxes(primitives)
    index = next(i for i, p in enumerate(primitives) if isinstance(p, Rect))
    x, y, w, h = result[index]
    result[index] = (x + 500, y, w, h)
    assert labels.moved(primitives, result, ()) is None


def test_a_missing_child_is_not_a_label_move() -> None:
    primitives = laid_out(sample_state())
    assert labels.moved(primitives, boxes(primitives)[:-1], ()) is None


def test_another_text_moved_by_hand_is_not_a_label_move() -> None:
    primitives = laid_out(sample_state())
    result = boxes(primitives)
    index = next(
        i for i, p in enumerate(primitives) if isinstance(p, Text) and p.role == "category"
    )
    x, y, w, h = result[index]
    result[index] = (x, y + 400, w, h)
    assert labels.moved(primitives, result, ()) is None


def test_stored_offsets_of_gone_labels_survive_a_move() -> None:
    gone = LabelOffset(LabelKey("value", 99, 0), 500.0, 500.0)
    state = replace(sample_state(), labels=(gone,))
    primitives = laid_out(state)
    key = LabelKey("total", 0)
    result = labels.moved(primitives, drag(primitives, key, 300.0, 0.0), state.labels)
    assert result == (gone, LabelOffset(key, 300.0, 0.0))


def test_dragging_a_label_in_a_sorted_chart_stores_the_data_sheet_index() -> None:
    state = changed(sample_state(), "sort=descending")
    primitives = laid_out(state)
    key = next(t.key for t in keyed_texts(state) if t.role == "total" and t.key)
    result = labels.moved(primitives, drag(primitives, key, 0.0, -500.0), ())
    assert result == (LabelOffset(key, 0.0, -500.0),)
    again = replace(state, labels=result)
    assert named(again, key).y == pytest.approx(named(state, key).y - 500)


def test_keyed_leaves_an_unsorted_chart_alone() -> None:
    primitives = laid_out(sample_state())
    assert labels.keyed(primitives, None) is primitives
    assert labels.keyed(primitives, (0, 1, 2, 3)) is primitives


# --- model and primitives ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "make",
    [
        lambda: LabelKey("name", 0),  # type: ignore[arg-type]
        lambda: LabelKey("value", -1),
        lambda: LabelKey("value", 0, -1),
        lambda: LabelOffset(LabelKey("total", 0), float("nan"), 0.0),
        lambda: LabelOffset(LabelKey("total", 0), 0.0, float("inf")),
    ],
)
def test_invalid_keys_and_offsets_are_rejected(make: object) -> None:
    with pytest.raises(ValueError, match=r"label|offset"):
        make()  # type: ignore[operator]


def test_a_state_takes_one_offset_per_label() -> None:
    key = LabelKey("total", 0)
    with pytest.raises(ValueError, match="one offset"):
        replace(sample_state(), labels=(LabelOffset(key, 1.0, 1.0), LabelOffset(key, 2.0, 2.0)))


def test_bounds_of_every_primitive() -> None:
    assert bounds(Rect(1, 2, 3, 4, 0)) == (1, 2, 3, 4)
    assert bounds(Text(1, 2, 3, 4, "x", "left", "value")) == (1, 2, 3, 4)
    assert bounds(Line(5, 9, 1, 2, "annotation")) == (1, 2, 4, 7)
    assert bounds(Polyline(((0, 10), (4, 2), (8, 6)), 0)) == (0, 2, 8, 8)
    assert bounds(Polygon(((1, 1), (5, 1), (3, 4)), 0)) == (1, 1, 4, 3)
    assert bounds(Marker(100, 100, 0)) == (-25, -25, 250, 250)
    assert bounds(Bubble(10, 20, 6, 0)) == (7, 17, 6, 6)


def test_a_hidden_label_shows_nothing_but_keeps_its_text() -> None:
    label = Text(0, 0, 1, 1, "42", "center", "value", hidden=True)
    assert label.shown == ""
    assert label.text == "42"


# --- sidebar ----------------------------------------------------------------------------------


def test_the_panel_offers_to_move_labels_and_to_reset_moved_ones() -> None:
    def format_commands(state: ChartState | None, usable: bool = True) -> list[str]:
        return [b.command.removeprefix(PROTOCOL) for b in content(state, usable, "en-US").format]

    assert "MoveLabels" in format_commands(sample_state())
    assert "ResetLabels" not in format_commands(sample_state())
    moved = replace(sample_state(), labels=(LabelOffset(LabelKey("total", 0), 0.0, -500.0),))
    commands = format_commands(moved)
    assert commands.index("MoveLabels") + 1 == commands.index("ResetLabels")
    assert "MoveLabels" not in format_commands(sample_gantt_state())
    assert "MoveLabels" not in format_commands(None)
    buttons = {b.command.removeprefix(PROTOCOL): b for b in content(moved, False, "de-DE").format}
    assert not buttons["MoveLabels"].enabled  # an orphaned chart cannot be edited
    assert buttons["MoveLabels"].title == "Beschriftungen verschieben"
