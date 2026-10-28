# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Annotations (difference and CAGR arrows) added through commands, in a real LibreOffice."""

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
)

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
        if child.ShapeType == "com.sun.star.drawing.LineShape" and child.LineEndName:
            assert len(child.LineEnd.Coordinates) > 0, "arrowhead has no shape"
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
        doc.close(True)


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
        doc.close(True)


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
                reloaded.close(True)
    finally:
        doc.close(True)


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
        doc.close(True)


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
        doc.close(True)
