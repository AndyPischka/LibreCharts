# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Gantt charts in a real LibreOffice: insert, dates in the data sheet, date lines, persistence."""

import datetime
import time

from helpers import (
    close_datasheets,
    close_doc,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    uno_command,
)

from librecharts.core.gantt import serial
from librecharts.lo import store

INSERT = "org.librecharts:InsertGanttChart"
EDIT = "org.librecharts:EditData"
DATE_LINE = "org.librecharts:AddAnnotation?kind=value_line&start=0&end=0&value={value}"
DATE_FORMAT = 2  # com.sun.star.util.NumberFormat.DATE


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _texts(group):
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.String:
            texts.append(child.String)
    return texts


def _shapes(group, kind):
    """(x, width, CharWeight or None) of every child of ``kind``, read in one pass."""
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType.endswith(kind):
            weight = child.CharWeight if kind == "TextShape" else None
            found.append((child.Position.X, child.Size.Width, weight, child.String))
    return found


def _wait_for(condition, seconds=10.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError("condition not reached in time")


def _size(width, height):
    import uno

    return uno.createUnoStruct("com.sun.star.awt.Size", width, height)


def _cell(calc, name):
    return calc.getSheets().getByIndex(0).getCellRangeByName(name)


def test_a_gantt_chart_draws_rows_milestones_and_bold_phases(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        state = _state(doc, chart_id)
        assert state.kind == "gantt"
        texts = _texts(group)
        for expected in ("Concept", "Testing", "Go-live", "Jan 2026", "Team A"):
            assert expected in texts, (expected, texts)
        assert len(_shapes(group, "PolyPolygonShape")) == 2  # milestones
        weights = {text: weight for _, _, weight, text in _shapes(group, "TextShape")}
        assert weights["Concept"] == 150  # a phase label is bold
        assert weights["Testing"] < 150
    finally:
        close_doc(doc)


def test_the_data_sheet_shows_dates_and_an_edited_date_moves_the_bar(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, EDIT)
        (calc,) = datasheets(ctx)
        formats = calc.getNumberFormats()
        for name in ("B3", "C3", "B20"):  # whole columns, new rows included
            key = _cell(calc, name).NumberFormat
            assert formats.getByKey(key).Type & DATE_FORMAT, name
        assert _cell(calc, "B3").getValue() == serial(datetime.date(2026, 1, 5))
        assert not calc.isModified()

        before = sorted(x for x, _, _, _ in _shapes(group, "RectangleShape"))
        _cell(calc, "B3").setValue(serial(datetime.date(2026, 1, 19)))  # Requirements
        _wait_for(lambda: _state(doc, chart_id).values[2][1] == serial(datetime.date(2026, 1, 19)))
        after = sorted(x for x, _, _, _ in _shapes(group, "RectangleShape"))
        assert after != before
        assert not calc.isModified()
    finally:
        close_datasheets(ctx)
        close_doc(doc)


def test_a_date_line_and_a_today_line_are_one_undo_step_each(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, DATE_LINE.format(value=serial(datetime.date(2026, 3, 16))))
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert any(text.startswith("16 Mar") or text.startswith("16.03.") for text in _texts(group))

        dispatch(ctx, doc, "org.librecharts:TodayLine")
        assert len(manager.getAllUndoActionTitles()) == depth + 2
        values = [a.value for a in _state(doc, chart_id).annotations]
        assert values == [
            serial(datetime.date(2026, 3, 16)),
            serial(datetime.date.today()),
        ]

        uno_command(ctx, doc, ".uno:Undo")
        assert len(_state(doc, chart_id).annotations) == 1
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).annotations == ()
    finally:
        close_doc(doc)


def test_sorting_by_start_date_is_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        _, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, "org.librecharts:ChangeChart?sort=ascending")
        assert _state(doc, chart_id).sort == "ascending"
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).sort == "none"
    finally:
        close_doc(doc)


def test_a_resize_keeps_the_milestones_small(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        diamonds = [width for _, width, _, _ in _shapes(group, "PolyPolygonShape")]
        bars = [width for _, width, _, _ in _shapes(group, "RectangleShape")]
        wide = group.Size.Width * 2
        group.Size = _size(wide, group.Size.Height)
        _wait_for(lambda: group.Size.Width == wide)
        _wait_for(lambda: [w for _, w, _, _ in _shapes(group, "RectangleShape")] != bars)
        time.sleep(0.5)
        resized = [width for _, width, _, _ in _shapes(group, "PolyPolygonShape")]
        assert all(abs(a - b) <= 2 for a, b in zip(resized, diamonds, strict=True))
    finally:
        close_doc(doc)


def test_a_gantt_chart_survives_reload(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, DATE_LINE.format(value=serial(datetime.date(2026, 3, 16))))
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                state = _state(reloaded, reloaded_id)
                assert state.kind == "gantt", fmt
                assert len(state.annotations) == 1, fmt
                if fmt == "odp":  # PPTX import turns polygons into custom shapes
                    assert len(_shapes(reloaded_group, "PolyPolygonShape")) == 2, fmt
                assert "Go-live" in _texts(reloaded_group), fmt
            finally:
                close_doc(reloaded)
    finally:
        close_doc(doc)
