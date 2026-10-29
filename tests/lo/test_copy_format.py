# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Copy chart format between charts in a real LibreOffice (ADR 0016)."""

from helpers import dispatch, first_page, new_impress, uno_command

from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def test_applying_without_a_copied_format_changes_nothing(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        before = _state(doc, chart_id)
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        doc.getCurrentController().select(group)
        dispatch(ctx, doc, "org.librecharts:ApplyChartFormat")

        assert _state(doc, chart_id) == before
        assert len(manager.getAllUndoActionTitles()) == depth
    finally:
        doc.close(True)


def test_a_copied_format_reaches_another_chart_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, INSERT)
        (group_a, id_a), (group_b, id_b) = store.find_charts(first_page(doc))
        controller = doc.getCurrentController()

        controller.select(group_a)
        dispatch(ctx, doc, "org.librecharts:ChangeFormat?axis=true")
        dispatch(ctx, doc, "org.librecharts:ChangeChart?color=0&palette=2")
        source = _state(doc, id_a)
        assert source.format.axis
        assert source.colors == (2,)

        controller.select(group_a)
        dispatch(ctx, doc, "org.librecharts:CopyChartFormat")
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        controller.select(group_b)
        dispatch(ctx, doc, "org.librecharts:ApplyChartFormat")

        applied = _state(doc, id_b)
        assert applied.format.axis
        assert applied.colors == (2,)
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")

        restored = _state(doc, id_b)
        assert not restored.format.axis
        assert restored.colors == ()
    finally:
        doc.close(True)
