# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Column + line combination charts and secondary axes in a real LibreOffice."""

import time

from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    uno_command,
)

from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
LINE_B = "org.librecharts:ChangeChart?line=1&on=true"
COLUMN_B = "org.librecharts:ChangeChart?line=1&on=false"
SECONDARY_B = "org.librecharts:ChangeChart?secondary=1&on=true"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _children(group):
    """(shape type, text) of every child, read in one pass (LibreOffice 26.8 geometry quirk)."""
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        found.append((child.ShapeType.rsplit(".", 1)[-1], child.String))
    return found


def _count(children, kind):
    return len([child for child in children if child[0] == kind])


def test_a_column_can_become_a_combination_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        before = _children(group)
        assert _count(before, "RectangleShape") == 10  # frame + nine bars
        assert _count(before, "PolyLineShape") == 0

        dispatch(ctx, doc, LINE_B)
        assert _state(doc, chart_id).lines == (1,)
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        merged = _children(group)
        assert _count(merged, "RectangleShape") == 7  # frame + the two column series
        assert _count(merged, "PolyLineShape") == 1
        assert _count(merged, "EllipseShape") == 3  # one marker per category

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).lines == ()
        assert _children(group) == before

        dispatch(ctx, doc, LINE_B)
        dispatch(ctx, doc, COLUMN_B)
        assert _state(doc, chart_id).lines == ()
        assert _count(_children(group), "PolyLineShape") == 0
    finally:
        doc.close(True)


def test_the_secondary_axis_is_drawn_even_without_the_value_axis(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        texts = [text for _, text in _children(group)]
        assert "0" not in texts  # the column chart has no value axis

        dispatch(ctx, doc, SECONDARY_B)
        state = _state(doc, chart_id)
        assert state.lines == (1,)
        assert state.secondary == (1,)
        assert not state.format.axis
        texts = [text for _, text in _children(group)]
        assert "0" in texts, texts  # the always-shown right axis
        assert _count(_children(group), "PolyLineShape") == 1
    finally:
        doc.close(True)


def test_combination_and_secondary_axis_survive_reload(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, SECONDARY_B)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id)
                assert restored.lines == (1,), fmt
                assert restored.secondary == (1,), fmt
                texts = [text for _, text in _children(reloaded_group) if text]
                assert "0" in texts, (fmt, texts)
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_a_data_sheet_edit_keeps_the_combination(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, LINE_B)

        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B3").setValue(40)
        _wait_for(lambda: _state(doc, chart_id).values[2][1] == 40.0)
        edited = _state(doc, chart_id)
        assert edited.lines == (1,)
        texts = [text for _, text in _children(group)]
        assert "40" in texts, texts  # the edited line point is labelled
        assert _count(_children(group), "PolyLineShape") == 1
    finally:
        close_datasheets(ctx)
        doc.close(True)
