# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Same-scale groups in a real LibreOffice (ADR 0017)."""

import time
from dataclasses import replace

import uno
from helpers import close_doc, dispatch, first_page, new_impress, set_chart_state, uno_command

from librecharts.core import style
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"


def _bar_heights(group):
    """Heights of the solid series shapes, in one pass (do not keep proxies)."""
    heights = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.FillStyle.value == "SOLID" and child.FillColor in style.PALETTE:
            heights.append(child.Size.Height)
    return heights


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _select(ctx, controller, *groups):
    collection = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.drawing.ShapeCollection", ctx
    )
    for group in groups:
        collection.add(group)
    controller.select(collection)


def _double(state):
    return replace(
        state,
        values=tuple(
            tuple(None if value is None else value * 2 for value in row) for row in state.values
        ),
    )


def test_two_charts_share_the_smallest_scale_and_undo_as_one_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, INSERT)
        charts = store.find_charts(first_page(doc))
        assert len(charts) == 2
        (group_a, id_a), (group_b, id_b) = charts
        set_chart_state(ctx, doc, id_b, _double(_state(doc, id_b)))

        before = max(_bar_heights(group_a))
        controller = doc.getCurrentController()
        _select(ctx, controller, group_a, group_b)
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, "org.librecharts:SameScale")

        group = _state(doc, id_a).scale_group
        assert group is not None
        assert _state(doc, id_b).scale_group == group
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        # Chart B needs half the length per unit, so A's columns become half as tall.
        assert max(_bar_heights(group_a)) < before

        uno_command(ctx, doc, ".uno:Undo")

        assert _state(doc, id_a).scale_group is None
        assert _state(doc, id_b).scale_group is None
        assert max(_bar_heights(group_a)) == before
    finally:
        close_doc(doc)


def test_removing_the_group_restores_the_own_scale(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, INSERT)
        (group_a, id_a), (group_b, id_b) = store.find_charts(first_page(doc))
        set_chart_state(ctx, doc, id_b, _double(_state(doc, id_b)))
        before = max(_bar_heights(group_a))
        controller = doc.getCurrentController()
        _select(ctx, controller, group_a, group_b)
        dispatch(ctx, doc, "org.librecharts:SameScale")
        scaled = max(_bar_heights(group_a))

        _select(ctx, controller, group_a, group_b)
        dispatch(ctx, doc, "org.librecharts:RemoveSameScale")

        assert _state(doc, id_a).scale_group is None
        assert _state(doc, id_b).scale_group is None
        assert max(_bar_heights(group_a)) == before
        assert scaled < before
    finally:
        close_doc(doc)


def test_the_shared_scale_survives_a_resize_of_one_chart(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, INSERT)
        (group_a, id_a), (group_b, id_b) = store.find_charts(first_page(doc))
        controller = doc.getCurrentController()
        _select(ctx, controller, group_a, group_b)
        dispatch(ctx, doc, "org.librecharts:SameScale")
        group = _state(doc, id_a).scale_group
        assert group is not None
        scaled = max(_bar_heights(group_a))

        group_b.Size = uno.createUnoStruct(
            "com.sun.star.awt.Size", group_b.Size.Width, group_b.Size.Height // 2
        )
        deadline = time.monotonic() + 5.0
        while max(_bar_heights(group_a)) >= scaled:
            assert time.monotonic() < deadline, "the group was not laid out again"
            time.sleep(0.05)

        assert _state(doc, id_a).scale_group == group
        assert _state(doc, id_b).scale_group == group
        # The smaller chart now limits the group, so the other one's columns shrink too.
        assert max(_bar_heights(group_a)) < scaled
    finally:
        close_doc(doc)
