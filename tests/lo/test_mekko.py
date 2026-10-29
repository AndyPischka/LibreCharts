# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Marimekko charts: insert, persist, and react to an added width row."""

import time

import uno
from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    uno_command,
    without_format,
)

from librecharts.core.datasheet import sample_mekko_state
from librecharts.lo import store

INSERT = "org.librecharts:InsertMekkoChart"
EDIT = "org.librecharts:EditData"
TO_UNITS = "org.librecharts:ChangeChart?percent=false"
TO_PERCENT = "org.librecharts:ChangeChart?percent=true"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _texts(group):
    """Strings of all text shapes, read in one pass (see AGENTS.md)."""
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType == "com.sun.star.drawing.TextShape":
            texts.append(child.String)
    return texts


def _bar_widths(group):
    widths = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType == "com.sun.star.drawing.RectangleShape":
            widths.append(child.Size.Width)
    return widths[1:]  # without the invisible frame


def test_mekko_is_inserted_and_survives_odp_and_pptx(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, chart_id),) = store.find_charts(first_page(doc))
        assert without_format(store.read_state(doc, chart_id)) == sample_mekko_state()
        texts = _texts(group)
        for expected in ("Europe", "Product A", "80", "50%"):  # Europe: A = 40 of 80
            assert expected in texts, (expected, texts)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert (
                    without_format(store.read_state(reloaded, reloaded_id)) == sample_mekko_state()
                ), fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_a_width_row_in_the_data_sheet_changes_the_column_widths(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, _),) = store.find_charts(first_page(doc))
        before = _bar_widths(group)
        dispatch(ctx, doc, EDIT)
        (calc,) = datasheets(ctx)
        sheet = calc.getSheets().getByIndex(0)
        sheet.insertCells(  # a new row 2 for the widths, as a user would add it
            sheet.getCellRangeByName("A2:E2").getRangeAddress(),
            uno.Enum("com.sun.star.sheet.CellInsertMode", "ROWS"),
        )
        sheet.getCellRangeByName("A2").setString("Width")
        for cell, value in (("B2", 10), ("C2", 10), ("D2", 10), ("E2", 10)):
            sheet.getCellRangeByName(cell).setValue(value)
        _wait_for(lambda: len(set(_bar_widths(group)[::3])) == 1)  # all columns equally wide now
        assert _bar_widths(group) != before
        assert "10" in _texts(group)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _units_chart(ctx):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)
    ((group, chart_id),) = store.find_charts(first_page(doc))
    dispatch(ctx, doc, TO_UNITS)
    return doc, group, chart_id


def test_switching_to_units_is_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, chart_id),) = store.find_charts(first_page(doc))
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        dispatch(ctx, doc, TO_UNITS)
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert not _state(doc, chart_id).percent
        texts = _texts(group)
        assert "15" in texts, texts  # Europe: Product C = 15 of 80
        assert "50%" not in texts, texts

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).percent
        assert "50%" in _texts(group)
        uno_command(ctx, doc, ".uno:Redo")
        assert not _state(doc, chart_id).percent
        dispatch(ctx, doc, TO_PERCENT)
        assert _state(doc, chart_id).percent
    finally:
        doc.close(True)


def test_the_units_variant_survives_odp_and_pptx(ctx):
    doc, _, _ = _units_chart(ctx)
    try:
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert not _state(reloaded, reloaded_id).percent, fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_a_data_sheet_edit_keeps_the_units_variant(ctx):
    doc, _, chart_id = _units_chart(ctx)
    try:
        dispatch(ctx, doc, EDIT)
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B2").setValue(50)
        _wait_for(lambda: _state(doc, chart_id).values[1][1] == 50.0)
        assert not _state(doc, chart_id).percent
    finally:
        close_datasheets(ctx)
        doc.close(True)
