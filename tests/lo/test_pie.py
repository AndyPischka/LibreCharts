# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Pie and doughnut charts in a real LibreOffice: segments, variant switch and persistence."""

from helpers import dispatch, first_page, new_impress, save_and_reload, uno_command

from librecharts.lo import store

INSERT = "org.librecharts:InsertPieChart"
TO_DOUGHNUT = "org.librecharts:ChangeChart?doughnut=true"
ADD = "org.librecharts:AddAnnotation?"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _children(group):
    """(shape type, text) of every child, read in one pass (LibreOffice 26.8 geometry quirk)."""
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        found.append((child.ShapeType.rsplit(".", 1)[-1], child.String))
    return found


def _segments(children):
    return [child for child in children if child[0] == "PolyPolygonShape"]


def test_a_pie_chart_draws_one_segment_per_series_and_category(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert _state(doc, chart_id).kind == "pie"
        children = _children(group)
        assert len(_segments(children)) == 6  # 3 products in 2 years
        texts = [text for _, text in children if text]
        for expected in ("2024", "2025", "40%", "35%", "25%"):
            assert expected in texts, (expected, texts)
        assert "Product A" in texts  # the legend column right of the pies
    finally:
        doc.close(True)


def test_the_doughnut_switch_is_one_undo_step_and_shows_the_sum(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, TO_DOUGHNUT)
        assert _state(doc, chart_id).doughnut
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        texts = [text for _, text in _children(group) if text]
        assert "100" in texts  # the sum of 2024 in the hole

        uno_command(ctx, doc, ".uno:Undo")
        assert not _state(doc, chart_id).doughnut
        assert "100" not in [text for _, text in _children(group)]
    finally:
        doc.close(True)


def test_a_resize_keeps_the_segments(ctx):
    import time

    import uno

    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        before = len(_children(group))
        wide = group.Size.Width * 2
        group.Size = uno.createUnoStruct("com.sun.star.awt.Size", wide, group.Size.Height)
        deadline = time.monotonic() + 10
        while group.Size.Width != wide and time.monotonic() < deadline:
            time.sleep(0.1)
        time.sleep(0.5)  # the resize watcher lays the chart out again
        assert len(_children(group)) == before
        assert len(_segments(_children(group))) == 6
    finally:
        doc.close(True)


def test_pie_and_doughnut_charts_survive_reload(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, TO_DOUGHNUT)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id)
                assert (restored.kind, restored.doughnut) == ("pie", True), fmt
                if fmt == "odp":  # PPTX import turns the polygons into custom shapes
                    assert len(_segments(_children(reloaded_group))) == 6, fmt
                texts = [text for _, text in _children(reloaded_group) if text]
                assert "100" in texts, (fmt, texts)
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_difference_arrows_between_segments_are_stored_and_drawn(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        # Product A's 2024 share (40 %) vs. Product B's 2025 share (38 %)
        dispatch(ctx, doc, ADD + "kind=difference&start=0&end=1&series=0&series_end=1")
        annotations = _state(doc, chart_id).annotations
        assert [(a.kind, a.start, a.end, a.series, a.series_end) for a in annotations] == [
            ("difference", 0, 1, 0, 1)
        ]
        assert "-5%" in [text for _, text in _children(group) if text]

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id).annotations
                assert [a.kind for a in restored] == ["difference"], fmt
                assert "-5%" in [text for _, text in _children(reloaded_group) if text], fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_a_difference_arrow_between_two_segments_of_one_pie_is_drawn(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        # between the segments of one pie: A's 40 % vs. B's 35 %
        dispatch(ctx, doc, ADD + "kind=difference&start=0&end=0&series=0&series_end=1")
        annotations = _state(doc, chart_id).annotations
        assert [(a.kind, a.series, a.series_end) for a in annotations] == [("difference", 0, 1)]
        assert "-12.5%" in [text for _, text in _children(group) if text]
    finally:
        doc.close(True)
