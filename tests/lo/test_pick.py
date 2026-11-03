# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Pick mode: annotations are placed by selecting columns inside the entered chart group.

A user's click inside the entered group selects the shape under the mouse; these tests select
the shapes directly (``controller.select``), which drives the same selection listener and works
in hidden documents.
"""

import time
from dataclasses import replace

import uno
from helpers import (
    dispatch,
    first_page,
    new_impress,
    set_chart_state,
    skip_on_headless_linux,
    without_format,
)

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


def test_picking_two_bars_of_one_category_adds_a_between_series_arrow(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        set_chart_state(ctx, doc, chart_id, replace(sample_state(), grouping="clustered"))
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        controller.select(_child_with_text(group, "10"))  # Product A's 2023 bar
        controller.select(_child_with_text(group, "20"))  # Product B's 2023 bar
        _wait_for(
            lambda: (
                _annotations(doc, chart_id)
                == (Annotation("difference", 0, 0, series=0, series_end=1),)
            )
        )
        assert "+100%" in [group.getByIndex(i).String for i in range(group.getCount())]  # 10 -> 20
    finally:
        doc.close(True)


def test_picking_two_categories_adds_a_category_gap(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "gap")
        controller.select(_child_with_text(group, "2023"))
        controller.select(_child_with_text(group, "2024"))
        _wait_for(lambda: _annotations(doc, chart_id) == (Annotation("category_gap", 0, 1),))
        _wait_for(lambda: _chart_selected(doc))
    finally:
        doc.close(True)


def test_picking_two_segments_adds_a_difference_arrow_to_a_mekko_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertMekkoChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        # make the share labels locale-independent (a new chart follows the UI locale)
        set_chart_state(ctx, doc, chart_id, without_format(store.read_state(doc, chart_id)))
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        # the sample Mekko's share labels: Product A in Europe (50 %) and in Asia (22.2 %)
        controller.select(_child_with_text(group, "50%"))
        controller.select(_child_with_text(group, "22.2%"))
        _wait_for(
            lambda: _annotations(doc, chart_id) == (Annotation("difference", 0, 2, series=0),)
        )
        _wait_for(lambda: _chart_selected(doc))
        assert "-55.6%" in [group.getByIndex(i).String for i in range(group.getCount())]
    finally:
        doc.close(True)


def test_picking_two_segments_of_one_column_adds_a_level_difference(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertMekkoChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        set_chart_state(ctx, doc, chart_id, without_format(store.read_state(doc, chart_id)))
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        # Product A (50 %) and Product B (31.2 %) of Europe: no side-by-side bars -> level arrow
        controller.select(_child_with_text(group, "50%"))
        controller.select(_child_with_text(group, "31.2%"))
        _wait_for(
            lambda: (
                _annotations(doc, chart_id)
                == (Annotation("difference", 0, 0, series=0, style="level", series_end=1),)
            )
        )
    finally:
        doc.close(True)


def test_picking_two_segments_adds_a_difference_arrow_to_a_pie_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertPieChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        # the sample pie's share labels: Product A of 2024 (40 %) and Product B of 2025 (38 %)
        controller.select(_child_with_text(group, "40%"))
        controller.select(_child_with_text(group, "38%"))
        _wait_for(
            lambda: (
                _annotations(doc, chart_id)
                == (Annotation("difference", 0, 1, series=0, series_end=1),)
            )
        )
        _wait_for(lambda: _chart_selected(doc))
        assert "-5%" in [group.getByIndex(i).String for i in range(group.getCount())]
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


def test_picking_two_bars_adds_a_difference_arrow_to_a_bar_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertBarChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        assert not _chart_selected(doc), "pick mode should have entered the chart group"

        controller.select(_child_with_text(group, "2023"))
        controller.select(_child_with_text(group, "2025"))
        _wait_for(lambda: _annotations(doc, chart_id) == (Annotation("difference", 0, 2),))
        _wait_for(lambda: _chart_selected(doc))
        assert "+28.6%" in [group.getByIndex(i).String for i in range(group.getCount())]
    finally:
        doc.close(True)


def test_picking_two_columns_adds_a_difference_arrow_to_a_waterfall_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertWaterfallChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        controller = doc.getCurrentController()
        dispatch(ctx, doc, PICK + "difference")
        assert not _chart_selected(doc), "pick mode should have entered the chart group"

        controller.select(_child_with_text(group, "Start"))
        controller.select(_child_with_text(group, "End"))
        _wait_for(lambda: _annotations(doc, chart_id) == (Annotation("difference", 0, 5),))
        _wait_for(lambda: _chart_selected(doc))
        assert "+10%" in [group.getByIndex(i).String for i in range(group.getCount())]
    finally:
        doc.close(True)
