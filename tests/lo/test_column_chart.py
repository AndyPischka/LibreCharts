# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Insert, persist and redraw a column chart in a real LibreOffice."""

from dataclasses import replace

from helpers import dispatch, first_page, new_impress, save_and_reload

from librecharts.core.datasheet import sample_state
from librecharts.lo import chart, store

INSERT = "org.librecharts:InsertColumnChart"


def test_insert_adds_one_anchored_group_with_stored_state(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        page = first_page(doc)
        assert page.getCount() == 1
        charts = store.find_charts(page)
        assert len(charts) == 1, f"expected one chart, found {charts}"
        group, chart_id = charts[0]
        assert group.ShapeType == "com.sun.star.drawing.GroupShape"
        assert group.getCount() > 10
        assert store.read_state(doc, chart_id) == sample_state()
    finally:
        doc.close(True)


def test_insert_is_one_undo_step_and_redoable(ctx):
    doc = new_impress(ctx)
    try:
        manager = doc.getUndoManager()
        undo_depth = len(manager.getAllUndoActionTitles())
        dispatch(ctx, doc, INSERT)
        assert len(manager.getAllUndoActionTitles()) == undo_depth + 1
        assert manager.getCurrentUndoActionTitle() == "Insert LibreCharts chart"

        manager.undo()
        assert first_page(doc).getCount() == 0
        manager.redo()
        charts = store.find_charts(first_page(doc))
        assert len(charts) == 1
        assert charts[0][0].getCount() > 10
    finally:
        doc.close(True)


def test_state_survives_odp_and_pptx(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                charts = store.find_charts(first_page(reloaded))
                assert len(charts) == 1, f"{fmt}: expected one chart, found {charts}"
                _, chart_id = charts[0]
                assert store.read_state(reloaded, chart_id) == sample_state(), fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_redraw_keeps_frame_and_replaces_children(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        position, size = group.Position, group.Size
        stacked_children = group.getCount()

        clustered = replace(sample_state(), grouping="clustered")
        chart.redraw(doc, group, clustered)

        assert (group.Position.X, group.Position.Y) == (position.X, position.Y)
        assert (group.Size.Width, group.Size.Height) == (size.Width, size.Height)
        # stacked: per category 3 bars, 3 values, 1 total, 1 name; clustered has no total
        assert stacked_children - group.getCount() == 3
        assert store.read_state(doc, chart_id) == clustered
    finally:
        doc.close(True)


def test_redraw_is_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        stacked_children = group.getCount()
        chart.redraw(doc, group, replace(sample_state(), grouping="clustered"))

        manager = doc.getUndoManager()
        assert manager.getCurrentUndoActionTitle() == "Update LibreCharts chart"
        manager.undo()
        assert group.getCount() == stacked_children
        assert store.read_state(doc, chart_id) == sample_state()
        assert manager.getCurrentUndoActionTitle() == "Insert LibreCharts chart"
    finally:
        doc.close(True)
