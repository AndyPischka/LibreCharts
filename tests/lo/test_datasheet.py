# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Edit chart data in a Calc window, driven through the menu commands."""

import time

from helpers import close_datasheets, datasheets, dispatch, first_page, new_impress

from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
EDIT = "org.librecharts:EditData"


def _chart_with_open_datasheet(ctx):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)  # inserting selects the new chart
    dispatch(ctx, doc, EDIT)
    group, chart_id = store.find_charts(first_page(doc))[0]
    sheets = datasheets(ctx)
    assert len(sheets) == 1, f"expected one data sheet, found {len(sheets)}"
    return doc, group, chart_id, sheets[0]


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _cell(calc, name):
    return calc.getSheets().getByIndex(0).getCellRangeByName(name)


def test_datasheet_shows_the_stored_cells(ctx):
    doc, _, _, calc = _chart_with_open_datasheet(ctx)
    try:
        assert _cell(calc, "A2").getFormula() == "Product A"
        assert _cell(calc, "B1").getFormula() == "2023"
        assert _cell(calc, "B2").getValue() == 10
        assert not calc.isModified()
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_editing_a_value_updates_state_and_chart(ctx):
    doc, group, chart_id, calc = _chart_with_open_datasheet(ctx)
    try:
        _cell(calc, "D4").setValue(90)  # Product C, 2025
        _wait_for(lambda: _state(doc, chart_id).values[3][3] == 90)
        labels = [group.getByIndex(i).String for i in range(group.getCount())]
        assert "90" in labels
        assert "126" in labels  # new 2025 total: 15 + 21 + 90
        assert not calc.isModified(), "closing the data sheet would ask to save"
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_formula_survives_closing_and_reopening(ctx):
    doc, group, chart_id, calc = _chart_with_open_datasheet(ctx)
    try:
        _cell(calc, "B2").setFormula("=4*5")
        _wait_for(lambda: _state(doc, chart_id).cells[1][1] == "=4*5")
        assert _state(doc, chart_id).values[1][1] == 20
        calc.close(True)
        assert datasheets(ctx) == []

        doc.getCurrentController().select(group)
        dispatch(ctx, doc, EDIT)
        (reopened,) = datasheets(ctx)
        assert _cell(reopened, "B2").getFormula() == "=4*5"
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_editing_again_reuses_the_open_window(ctx):
    doc, _, _, _ = _chart_with_open_datasheet(ctx)
    try:
        dispatch(ctx, doc, EDIT)
        assert len(datasheets(ctx)) == 1
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_datasheet_of_a_hidden_presentation_is_hidden(ctx):
    doc, _, _, calc = _chart_with_open_datasheet(ctx)
    try:
        assert not calc.getCurrentController().getFrame().getContainerWindow().isVisible()
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_closing_the_presentation_closes_its_datasheet(ctx):
    doc, _, _, _ = _chart_with_open_datasheet(ctx)
    doc.close(True)
    _wait_for(lambda: datasheets(ctx) == [])
