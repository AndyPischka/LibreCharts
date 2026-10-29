# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Label placement: value labels and totals the user moved are stored as offsets (ADR 0023).

Labels are moved like a user does: the chart group is entered (*Move labels*) and a label is placed
with the position dialog, which LibreOffice records as one undo step. A real mouse drag, the info
bar and the look of *Move labels* are tested by hand.
"""

import time
from dataclasses import replace

import uno
from helpers import (
    dispatch,
    first_page,
    new_impress,
    prop,
    save_and_reload,
    set_chart_state,
    uno_command,
)

from librecharts.core import labels as core_labels
from librecharts.core.layout.chart import layout_chart
from librecharts.core.model import LabelKey, LabelOffset
from librecharts.core.primitives import Text
from librecharts.lo import labels, render, store

INSERT = "org.librecharts:InsertColumnChart"
MOVE = "org.librecharts:MoveLabels"
RESET = "org.librecharts:ResetLabels"
TOTAL = LabelKey("total", 0)
VALUE = LabelKey("value", 1, 0)


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _chart(ctx):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)  # inserting selects the new chart
    group, chart_id = store.find_charts(first_page(doc))[0]
    return doc, group, chart_id


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _offsets(doc, chart_id):
    return {o.key: (round(o.dx), round(o.dy)) for o in _state(doc, chart_id).labels}


def _child(group, state, key):
    """The label shape of ``key``: the primitives follow the frame, one child each."""
    _, _, width, height = render.layout_box(group)
    for index, p in enumerate(layout_chart(state, width, height)):
        if isinstance(p, Text) and p.key == key:
            return group.getByIndex(index + 1)
    raise AssertionError(f"no label {key}")


def _text_child(group, text):
    for i in range(1, group.getCount()):
        child = group.getByIndex(i)
        if child.String == text:
            return child
    raise AssertionError(f"no child {text!r}")


def _edited(state):
    """``state`` with other numbers in its first series."""
    return replace(
        state,
        cells=(state.cells[0], ("Product A", "30", "10", "50"), *state.cells[2:]),
        values=(state.values[0], (None, 30.0, 10.0, 50.0), *state.values[2:]),
    )


def _enter(ctx, doc, group):
    """Enter the chart like the *Move labels* command does."""
    doc.getCurrentController().select(group)
    dispatch(ctx, doc, MOVE)


def _place(ctx, doc, child, dx, dy):
    """Move ``child`` by (``dx``, ``dy``) with the position dialog: one undo step in LibreOffice."""
    doc.getCurrentController().select(child)
    position = child.Position
    uno_command(
        ctx,
        doc,
        ".uno:TransformDialog",
        (prop("TransformPosX", position.X + dx), prop("TransformPosY", position.Y + dy)),
    )


def _consistent(doc, group, chart_id):
    """Whether the shapes show exactly what the stored state lays out."""
    state = _state(doc, chart_id)
    _, _, width, height = render.layout_box(group)
    primitives = layout_chart(state, width, height)
    return core_labels.moved(primitives, labels.read_boxes(group), state.labels) == state.labels


def _resize(group, width, height):
    group.Size = uno.createUnoStruct("com.sun.star.awt.Size", width, height)


def test_moving_a_total_stores_its_offset(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        before = _child(group, _state(doc, chart_id), TOTAL).Position
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        assert _offsets(doc, chart_id)[TOTAL] == (500, -300)
        moved = _child(group, _state(doc, chart_id), TOTAL).Position
        assert (moved.X - before.X, moved.Y - before.Y) == (500, -300)
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_moving_a_value_label_out_of_its_segment_recolours_and_shows_it(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        label = _child(group, _state(doc, chart_id), VALUE)
        inside = label.CharColor
        _place(ctx, doc, label, 0, -7500)
        _wait_for(lambda: VALUE in _offsets(doc, chart_id))
        moved = _child(group, _state(doc, chart_id), VALUE)
        assert moved.String
        _wait_for(lambda: moved.CharColor != inside)
    finally:
        doc.close(True)


def test_undo_clears_the_offset_and_redo_restores_it(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 400, -200)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:Undo")
        _wait_for(lambda: not _offsets(doc, chart_id))
        assert _consistent(doc, group, chart_id)
        uno_command(ctx, doc, ".uno:Redo")
        _wait_for(lambda: _offsets(doc, chart_id).get(TOTAL) == (400, -200))
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_a_label_dragged_back_onto_its_place_snaps_there(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 600, 0)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), -550, 0)
        _wait_for(lambda: not _offsets(doc, chart_id))
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_offsets_survive_data_edits_sorting_and_a_new_scheme(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        state = _state(doc, chart_id)
        doc.getCurrentController().select(group)
        edited = _edited(state)
        set_chart_state(ctx, doc, chart_id, edited)
        assert _offsets(doc, chart_id)[TOTAL] == (500, -300)
        assert _consistent(doc, group, chart_id)
        dispatch(ctx, doc, "org.librecharts:ChangeChart?sort=descending")
        assert _offsets(doc, chart_id)[TOTAL] == (500, -300)
        assert _consistent(doc, group, chart_id)
        dispatch(ctx, doc, "org.librecharts:SetScheme?name=Grey")
        assert _offsets(doc, chart_id)[TOTAL] == (500, -300)
    finally:
        doc.close(True)


def test_a_resize_keeps_the_label_at_its_distance(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:LeaveGroup")
        _, _, width, height = render.layout_box(group)
        _resize(group, width, height * 2)
        _wait_for(lambda: render.layout_box(group)[3] == height * 2)
        _wait_for(lambda: _consistent(doc, group, chart_id))
        assert _offsets(doc, chart_id)[TOTAL] == (500, -300)  # absolute, not scaled
    finally:
        doc.close(True)


def test_a_label_moved_out_of_the_frame_does_not_count_as_a_resize(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        before = render.layout_box(group)
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 0, -3000)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        time.sleep(0.5)
        assert render.layout_box(group) == before
        assert group.Size.Height > before[3]  # the group grew, the layout box did not
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_a_value_edit_redraws_in_place_so_older_undo_steps_keep_working(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:LeaveGroup")
        shapes = [group.getByIndex(i) for i in range(group.getCount())]
        state = _state(doc, chart_id)
        edited = _edited(state)
        doc.getCurrentController().select(group)
        set_chart_state(ctx, doc, chart_id, edited)
        assert [group.getByIndex(i) for i in range(group.getCount())] == shapes
        uno_command(ctx, doc, ".uno:Undo")  # the edit
        uno_command(ctx, doc, ".uno:Undo")  # the move
        _wait_for(lambda: not _offsets(doc, chart_id))
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_reset_label_positions_is_one_undo_step(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        _place(ctx, doc, _child(group, _state(doc, chart_id), VALUE), 0, -4000)
        _wait_for(lambda: VALUE in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:LeaveGroup")
        doc.getCurrentController().select(group)
        dispatch(ctx, doc, RESET)
        assert not _offsets(doc, chart_id)
        assert _consistent(doc, group, chart_id)
        uno_command(ctx, doc, ".uno:Undo")
        _wait_for(lambda: set(_offsets(doc, chart_id)) == {TOTAL, VALUE})
        assert _consistent(doc, group, chart_id)
    finally:
        doc.close(True)


def test_any_other_text_dragged_by_hand_is_put_back(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        category = _text_child(group, "2023")
        home = (category.Position.X, category.Position.Y)
        _place(ctx, doc, category, 700, -500)
        _wait_for(lambda: home == (category.Position.X, category.Position.Y))
        assert not _offsets(doc, chart_id)
    finally:
        doc.close(True)


def test_offsets_survive_odp_and_pptx(ctx):
    doc, group, chart_id = _chart(ctx)
    reloaded = []
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:LeaveGroup")
        for fmt in ("odp", "pptx"):
            again = save_and_reload(ctx, doc, fmt)
            reloaded.append(again)
            again_group, again_id = store.find_charts(first_page(again))[0]
            assert _offsets(again, again_id) == {TOTAL: (500, -300)}
            assert _consistent(again, again_group, again_id)
    finally:
        for again in reloaded:
            again.close(True)
        doc.close(True)


def test_a_variant_change_clears_the_offsets(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        _enter(ctx, doc, group)
        _place(ctx, doc, _child(group, _state(doc, chart_id), TOTAL), 500, -300)
        _wait_for(lambda: TOTAL in _offsets(doc, chart_id))
        uno_command(ctx, doc, ".uno:LeaveGroup")
        doc.getCurrentController().select(group)
        dispatch(ctx, doc, "org.librecharts:ChangeChart?grouping=clustered")
        assert not _offsets(doc, chart_id)
    finally:
        doc.close(True)


def test_picking_a_moved_label_picks_its_own_column(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        state = _state(doc, chart_id)
        moved = replace(state, labels=(LabelOffset(TOTAL, 11000.0, 0.0),))
        set_chart_state(ctx, doc, chart_id, moved)
        _wait_for(lambda: _consistent(doc, group, chart_id))
        doc.getCurrentController().select(group)
        dispatch(ctx, doc, "org.librecharts:PickAnnotation?kind=difference")
        label = _child(group, _state(doc, chart_id), TOTAL)
        doc.getCurrentController().select(label)  # the total of column 0, drawn above column 2
        time.sleep(0.3)
        doc.getCurrentController().select(_text_child(group, "2025"))
        _wait_for(lambda: bool(_state(doc, chart_id).annotations))
        annotation = _state(doc, chart_id).annotations[0]
        assert (annotation.start, annotation.end) == (0, 2)
    finally:
        doc.close(True)
