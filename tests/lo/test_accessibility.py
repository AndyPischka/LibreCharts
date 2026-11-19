# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Alternative text, patterns and CSV export in a real LibreOffice (M20, ADR 0030)."""

import csv
import tempfile
from pathlib import Path

import uno
from helpers import dispatch, first_page, new_impress, save_and_reload, uno_command

from librecharts.core import alttext, csvexport
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
PATTERNS = "org.librecharts:ChangeFormat?patterns=true"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _fill_styles(group):
    return [
        child.FillStyle.value
        for i in range(group.getCount())
        if (child := group.getByIndex(i)).ShapeType == "com.sun.star.drawing.RectangleShape"
        and child.FillStyle.value != "NONE"
    ]


def test_a_chart_carries_alternative_text_from_its_data(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        state = _state(doc, chart_id)  # in the UI language, like the chart's labels
        assert group.Title == alttext.title(state)
        assert group.Description == alttext.description(state)
        assert "Product A: 2023 = 10" in group.Description

        # ODP keeps the text; LibreOffice's PPTX filter drops it from groups (ADR 0030).
        reloaded = save_and_reload(ctx, doc, "odp")
        try:
            group, _ = store.find_charts(first_page(reloaded))[0]
            assert "Product A: 2023 = 10" in group.Description
        finally:
            reloaded.close(True)
    finally:
        doc.close(True)


def test_patterns_hatch_the_series_and_undo_as_one_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        assert set(_fill_styles(group)) == {"SOLID"}
        depth = len(doc.getUndoManager().getAllUndoActionTitles())

        dispatch(ctx, doc, PATTERNS)

        styles = _fill_styles(group)
        assert "HATCH" in styles
        assert "SOLID" in styles  # the first series stays plain colour
        assert _state(doc, chart_id).format.patterns
        assert len(doc.getUndoManager().getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")

        assert set(_fill_styles(group)) == {"SOLID"}
    finally:
        doc.close(True)


def test_the_data_exports_as_csv(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        path = Path(tempfile.mkdtemp(prefix="librecharts_")) / "data.csv"
        url = uno.systemPathToFileUrl(str(path))
        depth = len(doc.getUndoManager().getAllUndoActionTitles())

        dispatch(ctx, doc, f"org.librecharts:ExportCsv?url={url}")

        _, chart_id = store.find_charts(first_page(doc))[0]
        delimiter = csvexport.delimiter(_state(doc, chart_id))
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream, delimiter=delimiter))
        assert rows[0] == ["", "2023", "2024", "2025"]
        assert rows[1] == ["Product A", "10", "12", "15"]
        assert len(doc.getUndoManager().getAllUndoActionTitles()) == depth
    finally:
        doc.close(True)
