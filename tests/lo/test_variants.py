# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""M15 variants on a real LibreOffice: floating bars, error bars, waterfall variants, pie sort."""

from helpers import (
    close_datasheets,
    dispatch,
    first_page,
    new_impress,
    save_and_reload,
    uno_command,
)

from librecharts.lo import store

INSERT_COLUMN = "org.librecharts:InsertColumnChart"
INSERT_WATERFALL = "org.librecharts:InsertWaterfallChart"
INSERT_PIE = "org.librecharts:InsertPieChart"
FLOATING = "org.librecharts:ChangeChart?range=true"
NO_FLOATING = "org.librecharts:ChangeChart?range=false"
ERRORS = "org.librecharts:ChangeChart?errors=true"
HORIZONTAL = "org.librecharts:ChangeChart?horizontal=true"
STACKED = "org.librecharts:ChangeChart?stacked=true"
SORT_SEGMENTS = "org.librecharts:ChangeChart?sort=descending"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def test_floating_bars_and_error_bars_are_one_undo_step_each_and_survive_a_round_trip(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT_COLUMN)
        _, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, FLOATING)
        assert _state(doc, chart_id).range is True
        dispatch(ctx, doc, NO_FLOATING)
        dispatch(ctx, doc, ERRORS)
        state = _state(doc, chart_id)
        assert state.errors is True
        assert state.range is False
        assert len(manager.getAllUndoActionTitles()) == depth + 3

        uno_command(ctx, doc, ".uno:Undo")  # no error bars again
        assert _state(doc, chart_id).errors is False
        uno_command(ctx, doc, ".uno:Undo")  # floating bars again
        assert _state(doc, chart_id).range is True

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).range is True, fmt
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_waterfall_variants_apply_and_survive_a_round_trip(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT_WATERFALL)
        _, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, HORIZONTAL)
        assert _state(doc, chart_id).horizontal is True
        dispatch(ctx, doc, STACKED)
        state = _state(doc, chart_id)
        assert state.stacked is True
        assert state.horizontal is True

        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((_, reloaded_id),) = store.find_charts(first_page(reloaded))
                saved = _state(reloaded, reloaded_id)
                assert saved.horizontal is True, fmt
                assert saved.stacked is True, fmt
            finally:
                reloaded.close(True)
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_pie_segment_sorting_applies(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT_PIE)
        _, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, SORT_SEGMENTS)
        assert _state(doc, chart_id).sort == "descending"
    finally:
        close_datasheets(ctx)
        doc.close(True)
