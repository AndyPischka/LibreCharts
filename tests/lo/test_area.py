# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Area charts in a real LibreOffice: filled areas, shares, value lines and persistence."""

from helpers import close_doc, dispatch, first_page, new_impress, save_and_reload, uno_command

from librecharts.core.layout.common import format_share
from librecharts.lo import store

INSERT = "org.librecharts:InsertAreaChart"
TO_PERCENT = "org.librecharts:ChangeChart?percent=true"
TO_STACKED = "org.librecharts:ChangeChart?grouping=stacked"
VALUE_LINE = "org.librecharts:AddAnnotation?kind=value_line&start=0&end=0&value=30"


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


def _of_type(children, kind):
    return [child for child in children if child[0] == kind]


def test_an_area_chart_draws_one_filled_area_per_series(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert _state(doc, chart_id).kind == "area"
        children = _children(group)
        assert len(_of_type(children, "PolyPolygonShape")) == 2  # Revenue and Costs
        texts = [text for _, text in children if text]
        assert "Revenue" in texts
        assert "Costs" in texts
        assert "12" in texts
        assert "33" in texts
    finally:
        close_doc(doc)


def test_the_100_percent_variant_shows_shares_and_can_be_undone(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, TO_PERCENT)
        state = _state(doc, chart_id)
        assert state.percent
        assert state.grouping == "stacked"
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        share = format_share(12 / 21 * 100, state.format)  # Revenue in 2020: 12 of 21
        texts = [text for _, text in _children(group)]
        assert share in texts, (share, texts)
        assert len(_of_type(_children(group), "PolyPolygonShape")) == 2

        uno_command(ctx, doc, ".uno:Undo")
        assert not _state(doc, chart_id).percent
        dispatch(ctx, doc, TO_STACKED)
        assert not _state(doc, chart_id).percent
    finally:
        close_doc(doc)


def test_a_value_line_is_the_area_charts_only_annotation(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, VALUE_LINE)
        assert [(a.kind, a.value) for a in _state(doc, chart_id).annotations] == [
            ("value_line", 30.0)
        ]
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert "30" in [text for _, text in _children(group)]

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).annotations == ()
    finally:
        close_doc(doc)


def test_an_area_chart_survives_reload_in_both_variants(ctx):
    for percent in (False, True):
        doc = new_impress(ctx)
        try:
            dispatch(ctx, doc, INSERT)
            if percent:
                dispatch(ctx, doc, TO_PERCENT)
            for fmt in ("odp", "pptx"):
                reloaded = save_and_reload(ctx, doc, fmt)
                try:
                    ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                    restored = _state(reloaded, reloaded_id)
                    assert restored.kind == "area", fmt
                    assert restored.percent is percent, fmt
                    texts = [text for _, text in _children(reloaded_group) if text]
                    assert "Revenue" in texts, (fmt, texts)
                finally:
                    close_doc(reloaded)
        finally:
            close_doc(doc)
