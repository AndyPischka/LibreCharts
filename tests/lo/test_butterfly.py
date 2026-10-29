# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Butterfly charts in a real LibreOffice: mirrored bars, sorting and persistence."""

from helpers import dispatch, first_page, new_impress, save_and_reload, uno_command

from librecharts.lo import store

INSERT = "org.librecharts:InsertButterflyChart"
SORT = "org.librecharts:ChangeChart?sort=descending"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _children(group):
    """(shape type, text, x) of every child, read in one pass (LibreOffice 26.8 geometry quirk)."""
    found = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        found.append((child.ShapeType.rsplit(".", 1)[-1], child.String, child.Position.X))
    return found


def _rectangles(children):
    return [child for child in children if child[0] == "RectangleShape"]


def _category_order(group):
    names = {"0-14", "15-29", "30-44", "45-59", "60+"}
    return [text for _, text, _ in _children(group) if text in names]


def test_a_butterfly_chart_mirrors_two_series_around_the_category_names(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert _state(doc, chart_id).kind == "butterfly"
        children = _children(group)
        texts = [text.replace(",", ".") for _, text, _ in children if text]  # locale: 6,5 or 6.5
        for expected in ("Men", "Women", "0-14", "60+", "6.5", "10.1"):
            assert expected in texts, (expected, texts)
        # frame + 10 bars + 2 legend swatches: bars exist on both sides of the centre
        positions = sorted({x for _, _, x in _rectangles(children)})
        assert len(positions) > 3
    finally:
        doc.close(True)


def test_sorting_reorders_the_categories_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        assert _category_order(group) == ["0-14", "15-29", "30-44", "45-59", "60+"]

        dispatch(ctx, doc, SORT)
        assert _state(doc, chart_id).sort == "descending"
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert _category_order(group) == ["30-44", "45-59", "60+", "15-29", "0-14"]

        uno_command(ctx, doc, ".uno:Undo")
        assert _category_order(group) == ["0-14", "15-29", "30-44", "45-59", "60+"]
    finally:
        doc.close(True)


def test_a_butterfly_chart_survives_reload_with_its_sort_order(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, SORT)
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((reloaded_group, reloaded_id),) = store.find_charts(first_page(reloaded))
                restored = _state(reloaded, reloaded_id)
                assert (restored.kind, restored.sort) == ("butterfly", "descending"), fmt
                assert _category_order(reloaded_group)[0] == "30-44", fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)
