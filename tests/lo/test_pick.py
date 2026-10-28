# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Pick mode: annotations are placed by selecting columns inside the entered chart group.

A user's click inside the entered group selects the shape under the mouse; these tests select
the shapes directly (``controller.select``), which drives the same selection listener and works
in hidden documents.
"""

import time
from dataclasses import replace

import uno
from helpers import dispatch, first_page, new_impress, set_chart_state, skip_on_headless_linux

from librecharts.core.datasheet import sample_state
from librecharts.core.model import Annotation
from librecharts.lo import commands, store

INSERT = "org.librecharts:InsertColumnChart"
PICK = "org.librecharts:PickAnnotation?kind="


def _chart(ctx, hidden=True):
    doc = new_impress(ctx, hidden=hidden)
    dispatch(ctx, doc, INSERT)  # inserting selects the new chart
    group, chart_id = store.find_charts(first_page(doc))[0]
    return doc, group, chart_id


def _child_with_text(group, label):
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.String == label:
            return child
    raise AssertionError(f"no child labelled {label!r}")


def _annotations(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state.annotations


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _settle():
    time.sleep(0.5)  # give a (wrongly) scheduled annotation time to appear


def _chart_selected(doc):
    return commands.selected_chart(doc.getCurrentController()) is not None


def test_picking_two_columns_adds_a_difference_arrow(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        controller = doc.getCurrentController()
        depth = len(doc.getUndoManager().getAllUndoActionTitles())
        dispatch(ctx, doc, PICK + "difference")
        assert not _chart_selected(doc), "pick mode should have entered the chart group"

        controller.select(_child_with_text(group, "2023"))
        controller.select(_child_with_text(group, "2025"))
        _wait_for(lambda: _annotations(doc, chart_id) == (Annotation("difference", 0, 2),))
        _wait_for(lambda: _chart_selected(doc))  # group left, chart selected again
        assert len(doc.getUndoManager().getAllUndoActionTitles()) == depth + 1
        assert "+28.6%" in [group.getByIndex(i).String for i in range(group.getCount())]
    finally:
        doc.close(True)


def test_picking_the_start_column_again_keeps_waiting(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "cagr")
        controller.select(_child_with_text(group, "2024"))
        controller.select(_child_with_text(group, "42"))  # 2024's total label
        _settle()
        assert _annotations(doc, chart_id) == ()
        controller.select(_child_with_text(group, "2025"))
        _wait_for(lambda: _annotations(doc, chart_id) == (Annotation("cagr", 1, 2),))
    finally:
        doc.close(True)


def test_picking_bars_of_a_clustered_chart_measures_that_series(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        set_chart_state(ctx, doc, chart_id, replace(sample_state(), grouping="clustered"))
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        # Product B's value labels sit above its bars: 20 (2023) and 21 (2025)
        controller.select(_child_with_text(group, "20"))
        controller.select(_child_with_text(group, "21"))
        _wait_for(lambda: len(_annotations(doc, chart_id)) == 1)
        assert _annotations(doc, chart_id) == (Annotation("difference", 0, 2, series=1),)
    finally:
        doc.close(True)


def test_selecting_something_outside_the_chart_cancels(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        page, controller = first_page(doc), doc.getCurrentController()
        other = doc.createInstance("com.sun.star.drawing.RectangleShape")
        page.add(other)
        other.Size = uno.createUnoStruct("com.sun.star.awt.Size", 1000, 1000)
        controller.select(group)
        dispatch(ctx, doc, PICK + "difference")
        controller.select(_child_with_text(group, "2023"))
        controller.select(other)
        _settle()
        controller.select(group)
        _settle()
        assert _annotations(doc, chart_id) == ()
        assert _chart_selected(doc)
    finally:
        doc.close(True)


def test_escape_cancels(ctx):
    skip_on_headless_linux("key events need a visible document, which aborts headless Linux")
    doc, group, chart_id = _chart(ctx, hidden=False)
    try:
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        controller.select(_child_with_text(group, "2023"))
        window = controller.getFrame().getComponentWindow()
        key = uno.createUnoStruct("com.sun.star.awt.KeyEvent")
        key.Source, key.KeyCode, key.KeyChar = window, 1281, chr(27)  # Key.ESCAPE
        robot = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        robot.keyPress(key)
        robot.keyRelease(key)
        _wait_for(lambda: _chart_selected(doc))
        controller.select(_child_with_text(group, "2025"))  # enters the group, no longer picks
        _settle()
        assert _annotations(doc, chart_id) == ()
    finally:
        doc.close(True)
