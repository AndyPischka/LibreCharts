# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Copies of a chart (paste, duplicated slide) are edited independently of the original."""

import time

from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    uno_command,
)

from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
EDIT = "org.librecharts:EditData"


def _inserted_and_pasted(ctx):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)
    page = first_page(doc)
    original, original_id = store.find_charts(page)[0]
    doc.getCurrentController().select(original)
    uno_command(ctx, doc, ".uno:Copy")
    uno_command(ctx, doc, ".uno:Paste")
    assert page.getCount() == 2
    copy = next(page.getByIndex(i) for i in range(2) if page.getByIndex(i) != original)
    return doc, page, copy, original_id


def test_pasted_chart_is_renamed_and_has_no_state_of_its_own(ctx):
    # This pins LibreOffice's behaviour that lo/store.py relies on (see its module docstring).
    doc, _, copy, original_id = _inserted_and_pasted(ctx)
    try:
        copy_id = store.chart_id_of(copy)
        assert copy_id is not None
        assert copy_id != original_id
        assert copy_id.split(" ")[0] == original_id  # new ids end in a letter: nothing is cut
        assert store.read_state(doc, copy_id) is None
    finally:
        doc.close(True)


def test_editing_a_pasted_chart_forks_it(ctx):
    doc, page, copy, original_id = _inserted_and_pasted(ctx)
    try:
        doc.getCurrentController().select(copy)
        dispatch(ctx, doc, EDIT)
        assert len(datasheets(ctx)) == 1

        ids = [chart_id for _, chart_id in store.find_charts(page)]
        assert len(set(ids)) == 2
        assert original_id in ids
        for chart_id in ids:
            assert store.read_state(doc, chart_id) is not None
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_editing_a_copy_does_not_touch_the_original(ctx):
    doc, _, copy, original_id = _inserted_and_pasted(ctx)
    try:
        doc.getCurrentController().select(copy)
        dispatch(ctx, doc, EDIT)
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B2").setValue(99)

        copy_id = store.chart_id_of(copy)
        assert copy_id is not None
        deadline = time.monotonic() + 5
        while True:
            state = store.read_state(doc, copy_id)
            if state is not None and state.values[1][1] == 99:
                break
            assert time.monotonic() < deadline, "edit did not reach the copy"
            time.sleep(0.05)
        original_state = store.read_state(doc, original_id)
        assert original_state is not None
        assert original_state.values[1][1] == 10
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_duplicated_slide_yields_independent_charts(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        uno_command(ctx, doc, ".uno:DuplicatePage")
        assert doc.getDrawPages().getCount() == 2
        second = doc.getDrawPages().getByIndex(1)
        copy, _ = store.find_charts(second)[0]
        doc.getCurrentController().setCurrentPage(second)
        doc.getCurrentController().select(copy)
        dispatch(ctx, doc, EDIT)
        ids = [chart_id for _, chart_id in store.all_charts(doc)]
        assert len(set(ids)) == len(ids)
        assert all(store.read_state(doc, i) is not None for i in ids)
    finally:
        close_datasheets(ctx)
        doc.close(True)
