# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Waterfall charts: insert, persist, and react to the total row of the data sheet."""

import time

from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
)

from librecharts.core.datasheet import sample_waterfall_state
from librecharts.lo import store

INSERT = "org.librecharts:InsertWaterfallChart"
EDIT = "org.librecharts:EditData"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _labels(group):
    """Texts of the value labels (read in one pass, see AGENTS.md)."""
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType == "com.sun.star.drawing.TextShape":
            texts.append(child.String)
    return texts


def test_waterfall_is_inserted_and_survives_odp_and_pptx(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, chart_id),) = store.find_charts(first_page(doc))
        assert group.getCount() > 20
        assert store.read_state(doc, chart_id) == sample_waterfall_state()
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert store.read_state(reloaded, reloaded_id) == sample_waterfall_state(), fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_sample_labels_show_steps_with_signs_and_the_computed_end_total(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, _),) = store.find_charts(first_page(doc))
        labels = _labels(group)
        for expected in ("100", "+30", "+15", "-25", "-10", "110"):
            assert expected in labels, (expected, labels)
    finally:
        doc.close(True)


def test_editing_a_value_and_the_total_row_redraws_the_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        ((group, chart_id),) = store.find_charts(first_page(doc))
        dispatch(ctx, doc, EDIT)
        (calc,) = datasheets(ctx)
        sheet = calc.getSheets().getByIndex(0)

        sheet.getCellRangeByName("C2").setValue(50)  # Growth: 30 -> 50, the end total follows
        _wait_for(lambda: "130" in _labels(group))
        assert "+50" in _labels(group)

        sheet.getCellRangeByName("D3").setString("x")  # "New markets" becomes a subtotal
        _wait_for(lambda: "+15" not in _labels(group))
        state = store.read_state(doc, chart_id)
        assert state is not None
        assert state.cells[2][3] == "x"
        assert not calc.isModified()
    finally:
        close_datasheets(ctx)
        doc.close(True)
