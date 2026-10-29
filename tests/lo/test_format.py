# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Chart format: axes, series names, number formats and value lines in a real LibreOffice."""

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

from librecharts.core import style
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
AXIS = "org.librecharts:ChangeFormat?axis=true"
GRIDLINES = "org.librecharts:ChangeFormat?gridlines=true"
LEGEND = "org.librecharts:ChangeFormat?series_names=legend"
VALUE_LINE = "org.librecharts:AddAnnotation?kind=value_line&start=0&end=0&value=40"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _texts(group):
    # PPTX import turns text boxes into custom shapes, so read every child's String.
    return [child.String for i in range(group.getCount()) if (child := group.getByIndex(i)).String]


def _text_colors(group):
    return {
        child.String: child.CharColor
        for i in range(group.getCount())
        if (child := group.getByIndex(i)).String
    }


def test_axis_gridlines_and_a_value_line_are_one_undo_step_each(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        assert "0" not in _texts(group)  # no axis yet

        dispatch(ctx, doc, AXIS)
        assert _state(doc, chart_id).format.axis
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert "0" in _texts(group), _texts(group)

        dispatch(ctx, doc, GRIDLINES)
        assert _state(doc, chart_id).format.gridlines
        assert len(manager.getAllUndoActionTitles()) == depth + 2

        uno_command(ctx, doc, ".uno:Undo")
        assert not _state(doc, chart_id).format.gridlines
        uno_command(ctx, doc, ".uno:Undo")
        assert not _state(doc, chart_id).format.axis

        dispatch(ctx, doc, VALUE_LINE)
        assert [(a.kind, a.value) for a in _state(doc, chart_id).annotations] == [
            ("value_line", 40.0)
        ]
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert "40" in _texts(group), _texts(group)
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).annotations == ()
    finally:
        doc.close(True)


def test_format_and_value_line_survive_reload_and_a_data_sheet_edit(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, LEGEND)
        dispatch(ctx, doc, VALUE_LINE)
        assert _state(doc, chart_id).format.series_names == "legend"
        assert "Product A" in _texts(group)

        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B2").setValue(50)
        _wait_for(lambda: _state(doc, chart_id).values[1][1] == 50.0)
        edited = _state(doc, chart_id)
        assert edited.format.series_names == "legend"
        assert [(a.kind, a.value) for a in edited.annotations] == [("value_line", 40.0)]

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id)
                assert restored.format.series_names == "legend", fmt
                assert [(a.kind, a.value) for a in restored.annotations] == [
                    ("value_line", 40.0)
                ], fmt
                texts = _texts(reloaded_group)
                assert "Product A" in texts, (fmt, texts)
                assert "40" in texts, (fmt, texts)
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_labels_on_a_dark_segment_are_white(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        colors = _text_colors(group)
        # Product B (20 in 2023) sits on the darkest palette colour, Product C (5) on the lightest.
        assert colors["20"] == style.WHITE, colors
        assert colors["5"] == style.BLACK, colors
    finally:
        doc.close(True)
