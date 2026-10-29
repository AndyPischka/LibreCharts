# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Chart options: variants and sorting on a real LibreOffice."""

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

from librecharts.core.datasheet import sample_state
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
TO_CLUSTERED = "org.librecharts:ChangeChart?grouping=clustered"
TO_STACKED = "org.librecharts:ChangeChart?grouping=stacked&percent=false"
TO_PERCENT = "org.librecharts:ChangeChart?percent=true"
SORT_DESCENDING = "org.librecharts:ChangeChart?sort=descending"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _texts(group):
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType == "com.sun.star.drawing.TextShape":
            texts.append(child.String)
    return texts


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def test_variants_are_one_undo_step_each(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, TO_CLUSTERED)
        assert _state(doc, chart_id).grouping == "clustered"
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        dispatch(ctx, doc, TO_PERCENT)
        state = _state(doc, chart_id)
        assert state.percent
        assert state.grouping == "stacked"
        assert "28.6%" in _texts(group), _texts(group)  # Product A in 2023: 10 of 35
        assert "35" in _texts(group)  # the absolute column sum stays visible

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).grouping == "clustered"
        uno_command(ctx, doc, ".uno:Redo")
        assert _state(doc, chart_id) == state
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).grouping == "clustered"
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id) == sample_state()
        dispatch(ctx, doc, TO_STACKED)
        assert _state(doc, chart_id) == sample_state()
    finally:
        doc.close(True)


def test_sort_survives_reload_and_a_data_sheet_edit(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, SORT_DESCENDING)
        assert _state(doc, chart_id).sort == "descending"
        texts = _texts(group)
        assert texts.index("2025") < texts.index("2024") < texts.index("2023")

        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B2").setValue(50)
        _wait_for(lambda: _state(doc, chart_id).values[1][1] == 50.0)
        assert _state(doc, chart_id).sort == "descending"

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).sort == "descending", fmt
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_an_arrow_stays_on_its_category_after_sorting(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, "org.librecharts:AddAnnotation?kind=difference&start=0&end=2")
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert "+28.6%" in _texts(group)
        dispatch(ctx, doc, SORT_DESCENDING)
        assert _state(doc, chart_id).sort == "descending"
        assert "+28.6%" in _texts(group), _texts(group)
        # The stored annotation keeps the data sheet indices.
        assert [(a.start, a.end) for a in _state(doc, chart_id).annotations] == [(0, 2)]
    finally:
        doc.close(True)
