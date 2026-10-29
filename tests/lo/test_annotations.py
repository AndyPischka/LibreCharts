# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Annotations (difference and CAGR arrows) added through commands, in a real LibreOffice."""

import time

import uno
from helpers import (
    close_datasheets,
    close_doc,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    set_chart_state,
    uno_command,
)

from librecharts.core.datasheet import state_from_table
from librecharts.core.layout.column import CATEGORY_BAND
from librecharts.core.model import Annotation
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
ADD = "org.librecharts:AddAnnotation?"
DIFFERENCE = ADD + "kind=difference&start=0&end=2"
ARROW_SHAPES = 4  # three lines and a label


def _chart(ctx):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)  # inserting selects the new chart
    group, chart_id = store.find_charts(first_page(doc))[0]
    return doc, group, chart_id


def _annotations(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state.annotations


def _labels(group):
    # PPTX import turns text boxes into custom shapes, so do not filter by shape type.
    return [group.getByIndex(i).String for i in range(group.getCount())]


def _arrowheads(group):
    count = 0
    for i in range(group.getCount()):
        child = group.getByIndex(i)  # read in one pass, see AGENTS.md
        if child.ShapeType != "com.sun.star.drawing.LineShape":
            continue
        # a line drawn right to left (or bottom to top) gets its head at the start
        if child.LineEndName:
            assert len(child.LineEnd.Coordinates) > 0, "arrowhead has no shape"
            count += 1
        elif child.LineStartName:
            assert len(child.LineStart.Coordinates) > 0, "arrowhead has no shape"
            count += 1
    return count


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def test_difference_arrow_is_stored_and_drawn(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        children = group.getCount()
        dispatch(ctx, doc, DIFFERENCE)
        assert _annotations(doc, chart_id) == (Annotation("difference", 0, 2),)
        assert group.getCount() == children + ARROW_SHAPES
        assert "+28.6%" in _labels(group)  # sample totals: 35 -> 45
        assert _arrowheads(group) == 1
    finally:
        close_doc(doc)


def test_adding_an_arrow_is_one_undo_step(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        children = group.getCount()
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        dispatch(ctx, doc, ADD + "kind=cagr&start=0&end=2&series=0")
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert "CAGR +22.5%" in _labels(group)  # Product A: 10 -> 15 over 2023..2025

        uno_command(ctx, doc, ".uno:Undo")
        assert _annotations(doc, chart_id) == ()
        assert group.getCount() == children
        uno_command(ctx, doc, ".uno:Redo")
        assert len(_annotations(doc, chart_id)) == 1
        assert group.getCount() == children + ARROW_SHAPES
    finally:
        close_doc(doc)


def test_arrows_survive_odp_and_pptx(ctx):
    doc, _, _ = _chart(ctx)
    try:
        dispatch(ctx, doc, DIFFERENCE)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                group, chart_id = store.find_charts(first_page(reloaded))[0]
                assert _annotations(reloaded, chart_id) == (Annotation("difference", 0, 2),), fmt
                assert "+28.6%" in _labels(group), fmt
                assert _arrowheads(group) == 1, fmt
            finally:
                close_doc(reloaded)
    finally:
        close_doc(doc)


def test_editing_data_keeps_an_arrow_added_while_the_data_sheet_is_open(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:EditData")
        calc = datasheets(ctx)[0]
        dispatch(ctx, doc, DIFFERENCE)
        calc.getSheets().getByIndex(0).getCellRangeByName("D2").setValue(25)  # Product A, 2025
        _wait_for(lambda: "+57.1%" in _labels(group))  # 35 -> 55
        assert _annotations(doc, chart_id) == (Annotation("difference", 0, 2),)
    finally:
        close_datasheets(ctx)
        close_doc(doc)


def test_resized_chart_keeps_its_arrow_laid_out(ctx):
    doc, group, _ = _chart(ctx)
    try:
        dispatch(ctx, doc, DIFFERENCE)
        size = group.Size
        group.Size = uno.createUnoStruct("com.sun.star.awt.Size", size.Width, size.Height * 2)

        def laid_out():
            for i in range(group.getCount()):
                child = group.getByIndex(i)
                if child.ShapeType.endswith("TextShape") and child.String == "2023":
                    return abs(child.Size.Height - CATEGORY_BAND) <= 1
            return False

        _wait_for(laid_out)
        assert "+28.6%" in _labels(group)
        assert _arrowheads(group) == 1
    finally:
        close_doc(doc)


def test_level_arrow_points_up_with_dashed_helper_lines(ctx):
    doc, group, _ = _chart(ctx)
    try:
        dispatch(ctx, doc, DIFFERENCE + "&style=level")  # 35 -> 45: the arrow points up
        dashed = start_heads = end_heads = 0
        for i in range(group.getCount()):
            child = group.getByIndex(i)  # read in one pass, see AGENTS.md
            if child.ShapeType != "com.sun.star.drawing.LineShape":
                continue
            dashed += child.LineStyle.value == "DASH"
            start_heads += bool(child.LineStartName)
            end_heads += bool(child.LineEndName)
        assert (dashed, start_heads, end_heads) == (2, 1, 0)
        assert "+28.6%" in _labels(group)
    finally:
        close_doc(doc)


def test_changing_and_removing_an_arrow_are_undo_steps(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        children = group.getCount()
        dispatch(ctx, doc, DIFFERENCE)
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, "org.librecharts:ChangeAnnotation?index=0&label=absolute")
        assert "+10" in _labels(group)
        dispatch(ctx, doc, "org.librecharts:ChangeAnnotation?index=0&style=level")
        assert _annotations(doc, chart_id) == (
            Annotation("difference", 0, 2, style="level", label="absolute"),
        )
        dispatch(ctx, doc, "org.librecharts:RemoveAnnotation?index=0")
        assert _annotations(doc, chart_id) == ()
        assert group.getCount() == children
        assert len(manager.getAllUndoActionTitles()) == depth + 3

        uno_command(ctx, doc, ".uno:Undo")
        assert len(_annotations(doc, chart_id)) == 1
    finally:
        close_doc(doc)


def test_remove_all_annotations(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        children = group.getCount()
        dispatch(ctx, doc, DIFFERENCE)
        dispatch(ctx, doc, ADD + "kind=cagr&start=0&end=1")
        dispatch(ctx, doc, "org.librecharts:RemoveAnnotations")
        assert _annotations(doc, chart_id) == ()
        assert group.getCount() == children
    finally:
        close_doc(doc)


def test_axis_break_cuts_a_tall_column_with_a_white_gap(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        tall = state_from_table(
            "column", "stacked", [[None, "2023", "2024", "2025"], ["Sales", 10, 12, 100]]
        )
        set_chart_state(ctx, doc, chart_id, tall)
        dispatch(ctx, doc, ADD + "kind=axis_break")
        assert _annotations(doc, chart_id) == (Annotation("axis_break", 0, 0),)
        assert _white_gaps(group) == 1
        assert "100" in _labels(group)  # the label keeps the real value
    finally:
        close_doc(doc)


def _white_gaps(group):
    gaps = 0
    for i in range(group.getCount()):
        child = group.getByIndex(i)  # read in one pass, see AGENTS.md
        if child.ShapeType.endswith("RectangleShape") and child.FillStyle.value == "SOLID":
            gaps += child.FillColor == 0xFFFFFF
    return gaps


def test_a_manual_axis_break_cuts_every_column_beyond_it_and_a_new_one_replaces_it(ctx):
    doc, group, chart_id = _chart(ctx)
    try:
        table = [[None, "2023", "2024", "2025"], ["Sales", 10, 100, 90]]
        set_chart_state(ctx, doc, chart_id, state_from_table("column", "stacked", table))
        dispatch(ctx, doc, ADD + "kind=axis_break&lower=30&upper=60")
        assert _annotations(doc, chart_id) == (Annotation("axis_break", 0, 0, lower=30, upper=60),)
        assert _white_gaps(group) == 2  # 2024 and 2025 reach beyond 30

        dispatch(ctx, doc, ADD + "kind=axis_break&lower=95&upper=99")
        assert _annotations(doc, chart_id) == (Annotation("axis_break", 0, 0, lower=95, upper=99),)
        assert _white_gaps(group) == 1  # only 2024 reaches beyond 95
        assert "100" in _labels(group)
        uno_command(ctx, doc, ".uno:Undo")
        assert _white_gaps(group) == 2
    finally:
        close_doc(doc)


def test_changing_the_range_of_an_axis_break(ctx):
    doc, _, chart_id = _chart(ctx)
    try:
        table = [[None, "2023", "2024", "2025"], ["Sales", 10, 100, 90]]
        set_chart_state(ctx, doc, chart_id, state_from_table("column", "stacked", table))
        dispatch(ctx, doc, ADD + "kind=axis_break")
        dispatch(ctx, doc, "org.librecharts:ChangeAnnotation?index=0&lower=30&upper=60")
        assert _annotations(doc, chart_id) == (Annotation("axis_break", 0, 0, lower=30, upper=60),)
        dispatch(ctx, doc, "org.librecharts:ChangeAnnotation?index=0&lower=&upper=")
        assert _annotations(doc, chart_id) == (Annotation("axis_break", 0, 0),)
    finally:
        close_doc(doc)


def test_bar_chart_arrows_and_axis_break_are_stored_and_drawn(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertBarChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, DIFFERENCE)
        dispatch(ctx, doc, ADD + "kind=difference&start=0&end=1&style=level")
        dispatch(ctx, doc, ADD + "kind=axis_break")
        assert [a.kind for a in _annotations(doc, chart_id)] == [
            "difference",
            "difference",
            "axis_break",
        ]
        assert "+28.6%" in _labels(group)
        assert _arrowheads(group) == 2
    finally:
        close_doc(doc)


def test_waterfall_arrows_and_a_break_below_the_steps_are_drawn(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertWaterfallChart")
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, ADD + "kind=difference&start=0&end=5")
        dispatch(ctx, doc, ADD + "kind=cagr&start=0&end=5")
        dispatch(ctx, doc, ADD + "kind=difference&start=0&end=5&style=level")
        dispatch(ctx, doc, ADD + "kind=axis_break")  # the sample's steps float above 100
        assert [a.kind for a in _annotations(doc, chart_id)] == [
            "difference",
            "cagr",
            "difference",
            "axis_break",
        ]
        labels = _labels(group)
        assert "+10%" in labels
        assert "CAGR +1.9%" in labels
        assert _arrowheads(group) == 3
        # the totals' break marks are white gaps; the steps keep their real labels
        assert "100" in labels
        assert "+30" in labels
    finally:
        close_doc(doc)
