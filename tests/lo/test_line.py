# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Line charts in a real LibreOffice: polylines, markers, names and persistence."""

import time

from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    uno_command,
)

from librecharts.core.model import Annotation
from librecharts.core.primitives import MARKER_SIZE
from librecharts.lo import store

INSERT = "org.librecharts:InsertLineChart"
HIDE_MARKERS = "org.librecharts:ChangeFormat?markers=false"
SHOW_MARKERS = "org.librecharts:ChangeFormat?markers=true"
INTERPOLATE = "org.librecharts:ChangeChart?interpolate=true"
ADD_MEDIAN = "org.librecharts:AddAnnotation?kind=value_line&mode=median"


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _children(group):
    """(shape type, text, position, size) of every child, read in one pass.

    Proxies collected in a list and read later intermittently reported default geometry
    (0, 0, 100, 100) in LibreOffice 26.8, so everything is read here.
    """
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        found.append(
            (
                child.ShapeType.rsplit(".", 1)[-1],
                child.String,
                (child.Position.X, child.Position.Y),
                (child.Size.Width, child.Size.Height),
            )
        )
    return found


def _of_type(children, kind):
    return [child for child in children if child[0] == kind]


def _line_segments(children):
    """The drawn series segments: polylines plus two-point runs, which LibreOffice stores as
    diagonal LineShapes (the horizontal baseline is a LineShape too and not counted)."""
    return len(_of_type(children, "PolyLineShape")) + len(
        [child for child in _of_type(children, "LineShape") if child[3][0] and child[3][1]]
    )


def test_a_line_chart_draws_one_polyline_per_series_with_markers(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert _state(doc, chart_id).kind == "line"
        children = _children(group)
        assert len(_of_type(children, "PolyLineShape")) == 2  # Revenue and Costs
        markers = _of_type(children, "EllipseShape")
        assert len(markers) == 12  # six years, two series
        assert all(size == (MARKER_SIZE, MARKER_SIZE) for *_, size in markers)
        texts = [text for _, text, _, _ in children if text]
        assert "Revenue" in texts
        assert "Costs" in texts
        assert "12" in texts
        assert "33" in texts
    finally:
        doc.close(True)


def test_markers_can_be_hidden_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, HIDE_MARKERS)
        assert _state(doc, chart_id).format.markers is False
        assert not _of_type(_children(group), "EllipseShape")
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        dispatch(ctx, doc, SHOW_MARKERS)
        assert len(_of_type(_children(group), "EllipseShape")) == 12
        assert len(manager.getAllUndoActionTitles()) == depth + 2

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).format.markers is False
        assert not _of_type(_children(group), "EllipseShape")
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).format.markers is True
        assert len(_of_type(_children(group), "EllipseShape")) == 12
    finally:
        doc.close(True)


def test_a_line_chart_survives_reload_and_a_data_sheet_edit(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, HIDE_MARKERS)

        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("B2").setValue(20)
        _wait_for(lambda: _state(doc, chart_id).values[1][1] == 20.0)
        edited = _state(doc, chart_id)
        assert edited.kind == "line"
        assert edited.format.markers is False
        texts = [text for _, text, _, _ in _children(group) if text]
        assert "20" in texts, texts

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id)
                assert restored.kind == "line", fmt
                assert restored.format.markers is False, fmt
                texts = [text for _, text, _, _ in _children(reloaded_group) if text]
                assert "Revenue" in texts, (fmt, texts)
                assert "20" in texts, (fmt, texts)
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_interpolation_bridges_a_gap_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        calc.getSheets().getByIndex(0).getCellRangeByName("D2").setString("")  # Revenue 2022 empty
        _wait_for(lambda: _state(doc, chart_id).values[1][3] is None)
        # gap mode: the Revenue line splits into two segments, the gap gets no marker or label
        _wait_for(lambda: _line_segments(_children(group)) == 3)
        assert len(_of_type(_children(group), "EllipseShape")) == 11
        texts = [text for _, text, _, _ in _children(group) if text]
        assert "18" not in texts  # the empty cell's value label is gone

        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        dispatch(ctx, doc, INTERPOLATE)
        assert _state(doc, chart_id).interpolate is True
        assert _line_segments(_children(group)) == 2  # one line per series again
        assert len(_of_type(_children(group), "EllipseShape")) == 11  # still no marker at the gap
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).interpolate is False
        assert _line_segments(_children(group)) == 3

        dispatch(ctx, doc, INTERPOLATE)
        assert _state(doc, chart_id).interpolate is True
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).interpolate is True, fmt
                if fmt == "odp":  # PPTX turns lines into custom shapes, so count only ODP's
                    assert _line_segments(_children(reloaded_group)) == 2, fmt
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_a_median_value_line_is_added_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        children = group.getCount()
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, ADD_MEDIAN)
        assert _state(doc, chart_id).annotations == (
            Annotation("value_line", 0, 0, value_line_mode="median"),
        )
        assert group.getCount() == children + 2  # the helper line and its label
        texts = [text for _, text, _, _ in _children(group) if text]
        # the median of the column sums 21, 25, 30, 36, 43, 52 is 33
        assert "33" in texts, texts
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).annotations == ()
        assert group.getCount() == children

        dispatch(ctx, doc, ADD_MEDIAN)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).annotations == (
                    Annotation("value_line", 0, 0, value_line_mode="median"),
                ), fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_a_resize_keeps_the_markers_small(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        big = group.Size.Height * 2
        group.Size = _size(group.Size.Width, big)
        _wait_for(lambda: group.Size.Height == big and _markers_small(group))
    finally:
        doc.close(True)


def _size(width, height):
    import uno

    return uno.createUnoStruct("com.sun.star.awt.Size", width, height)


def _markers_small(group):
    return all(
        size == (MARKER_SIZE, MARKER_SIZE)
        for *_, size in _of_type(_children(group), "EllipseShape")
    )
