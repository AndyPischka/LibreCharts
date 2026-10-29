# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Scatter and bubble charts in a real LibreOffice: markers, bubbles, resize and persistence."""

import time
from dataclasses import replace

from helpers import (
    close_doc,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    set_chart_state,
    without_format,
)

from librecharts.core.primitives import MARKER_SIZE
from librecharts.lo import store

INSERT = "org.librecharts:InsertScatterChart"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _ellipses(group):
    """(width, height, FillTransparence) of every ellipse child, read in one pass."""
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.ShapeType.endswith("EllipseShape"):
            found.append((child.Size.Width, child.Size.Height, child.FillTransparence))
    return found


def _texts(group):
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.String:
            texts.append(child.String)
    return texts


def _wait_for(condition, seconds=10.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError("condition not reached in time")


def _size(width, height):
    import uno

    return uno.createUnoStruct("com.sun.star.awt.Size", width, height)


def _with_sizes(state):
    """The sample state with a bubble size in every row."""
    values = tuple(
        row if r == 0 else (*row[:3], float(r * 10), *row[4:]) for r, row in enumerate(state.values)
    )
    return replace(state, values=values)


def test_a_scatter_chart_draws_markers_labels_axes_and_a_legend(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert _state(doc, chart_id).kind == "scatter"
        ellipses = _ellipses(group)
        assert len(ellipses) == 8
        assert {(w, h, t) for w, h, t in ellipses} == {(MARKER_SIZE, MARKER_SIZE, 0)}
        texts = _texts(group)
        for expected in ("Alpha", "Theta", "Group 1", "Group 2"):
            assert expected in texts, (expected, texts)
    finally:
        close_doc(doc)


def test_sizes_turn_markers_into_translucent_bubbles_that_follow_a_resize(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        sized = _with_sizes(without_format(_state(doc, chart_id)))
        set_chart_state(ctx, doc, chart_id, sized)
        _wait_for(lambda: len({w for w, _, _ in _ellipses(group)}) > 1)
        ellipses = _ellipses(group)
        assert len(ellipses) == 8
        assert all(w == h and transparence == 30 for w, h, transparence in ellipses)
        before = sorted(w for w, _, _ in ellipses)

        big = group.Size.Height * 2
        group.Size = _size(group.Size.Width * 2, big)
        _wait_for(lambda: group.Size.Height == big)
        _wait_for(lambda: sorted(w for w, _, _ in _ellipses(group)) != before)
        after = sorted(w for w, _, _ in _ellipses(group))
        # bubbles keep their proportions to each other
        assert abs(after[-1] / after[0] - before[-1] / before[0]) <= 0.02 * before[-1] / before[0]
    finally:
        close_doc(doc)


def test_a_resize_keeps_the_markers_small(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        big = group.Size.Height * 2
        group.Size = _size(group.Size.Width, big)
        _wait_for(lambda: group.Size.Height == big)
        time.sleep(0.5)
        assert {(w, h) for w, h, _ in _ellipses(group)} == {(MARKER_SIZE, MARKER_SIZE)}
    finally:
        close_doc(doc)


def test_gridlines_and_a_value_line_work_on_a_scatter_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, "org.librecharts:ChangeFormat?gridlines=true")
        assert _state(doc, chart_id).format.gridlines
        dispatch(ctx, doc, "org.librecharts:AddAnnotation?kind=value_line&start=0&end=0&value=40")
        assert [(a.kind, a.value) for a in _state(doc, chart_id).annotations] == [
            ("value_line", 40.0)
        ]
        assert "40" in _texts(group)
    finally:
        close_doc(doc)


def test_a_scatter_chart_survives_reload(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).kind == "scatter", fmt
                if fmt == "odp":  # PPTX import turns the ellipses into custom shapes
                    assert len(_ellipses(reloaded_group)) == 8, fmt
                assert "Alpha" in _texts(reloaded_group), fmt
            finally:
                close_doc(reloaded)
    finally:
        close_doc(doc)
