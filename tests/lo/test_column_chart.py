# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Insert, persist and redraw a column chart in a real LibreOffice."""

from dataclasses import replace

from helpers import dispatch, first_page, new_impress, save_and_reload, uno_command

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

        uno_command(ctx, doc, ".uno:Undo")
        assert first_page(doc).getCount() == 0
        uno_command(ctx, doc, ".uno:Redo")
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
        uno_command(ctx, doc, ".uno:Undo")
        assert group.getCount() == stacked_children
        assert store.read_state(doc, chart_id) == sample_state()
        assert manager.getCurrentUndoActionTitle() == "Insert LibreCharts chart"
    finally:
        doc.close(True)


def test_toolbar_is_registered_for_presentations(ctx):
    doc = new_impress(ctx)
    try:
        layout = doc.getCurrentController().getFrame().LayoutManager
        assert layout.getElement("private:resource/toolbar/addon_no.such.toolbar") is None
        toolbar = layout.getElement("private:resource/toolbar/addon_org.librecharts.toolbar")
        assert toolbar is not None, "LibreCharts toolbar not registered"
        assert toolbar.ResourceURL == "private:resource/toolbar/addon_org.librecharts.toolbar"
    finally:
        doc.close(True)


BAR_INSERT = "org.librecharts:InsertBarChart"


def test_bar_chart_is_inserted_and_survives_odp_and_pptx(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, BAR_INSERT)
        ((group, chart_id),) = store.find_charts(first_page(doc))
        assert group.getCount() > 10
        expected = replace(sample_state(), kind="bar")
        assert store.read_state(doc, chart_id) == expected
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert store.read_state(reloaded, reloaded_id) == expected, fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_bar_chart_is_redrawn_as_bars_after_a_data_change(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, BAR_INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        state = store.read_state(doc, chart_id)
        assert state is not None
        chart.redraw(doc, group, replace(state, grouping="clustered"))
        # Read the geometry in one pass: shape proxies held across further calls intermittently
        # reported default geometry (0, 0, 100, 100) in LibreOffice 26.8.
        rects = []
        for i in range(group.getCount()):
            child = group.getByIndex(i)
            if child.ShapeType == "com.sun.star.drawing.RectangleShape":
                rects.append(
                    (child.Position.X, child.Position.Y, child.Size.Width, child.Size.Height)
                )
        bars = rects[1:]  # the first rectangle is the invisible frame
        assert len(bars) == 9
        # first category: its three bars sit below each other and start at the same x (the baseline)
        first = bars[:3]
        assert len({x for x, _, _, _ in first}) == 1
        assert len({y for _, y, _, _ in first}) == 3
        assert [y for _, y, _, _ in first] == sorted(y for _, y, _, _ in first)
        # whereas column bars would sit side by side on the same bottom edge
        assert len({y + h for _, y, _, h in first}) == 3
        assert store.read_state(doc, chart_id) == replace(state, grouping="clustered")
    finally:
        doc.close(True)
