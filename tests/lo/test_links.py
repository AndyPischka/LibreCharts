# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Data links to Calc and Excel files in a real LibreOffice (ADR 0020).

The source workbooks are written by the tests into temp folders. The link dialog and the info
bars are tested by hand: headless LibreOffice returns from a modal dialog at once.
"""

import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

import uno
from helpers import (
    close_datasheets,
    datasheets,
    desktop,
    dispatch,
    first_page,
    new_impress,
    prop,
    save_and_reload,
    skip_on_headless_linux,
    uno_command,
)

from librecharts.core.links import same_file
from librecharts.lo import links, store

INSERT = "org.librecharts:InsertColumnChart"
CALC_FILTERS = {"ods": "calc8", "xlsx": "Calc MS Excel 2007 XML"}
DATA = (
    ("", "2024", "2025", "2026"),
    ("North", 10.0, 12.0, 15.0),
    ("South", 20.0, 22.0, 21.0),
)


def _folder():
    return Path(tempfile.mkdtemp(prefix="librecharts_links_"))


def _url(path):
    return uno.systemPathToFileUrl(str(path))


def _workbook(ctx, path, rows=DATA, names=()):
    """Write ``rows`` to the sheet "Data" of a new workbook at ``path`` (``.ods`` or ``.xlsx``);
    ``names`` are (name, Calc reference) pairs of named ranges."""
    calc = desktop(ctx).loadComponentFromURL(
        "private:factory/scalc", "_blank", 0, (prop("Hidden", True),)
    )
    try:
        sheet = calc.getSheets().getByIndex(0)
        sheet.setName("Data")
        width, height = len(rows[0]), len(rows)
        sheet.getCellRangeByPosition(0, 0, width - 1, height - 1).setDataArray(rows)
        origin = uno.createUnoStruct("com.sun.star.table.CellAddress", 0, 0, 0)
        for name, reference in names:
            calc.NamedRanges.addNewByName(name, reference, origin, 0)
        fmt = path.suffix[1:]
        calc.storeToURL(_url(path), (prop("FilterName", CALC_FILTERS[fmt]),))
    finally:
        calc.close(True)
    return path


def _change(ctx, path, cell, value):
    """Open the workbook at ``path``, set ``cell`` to ``value``, save and close it."""
    time.sleep(1.1)  # a new modification time even on file systems that keep whole seconds
    calc = desktop(ctx).loadComponentFromURL(_url(path), "_blank", 0, (prop("Hidden", True),))
    try:
        calc.getSheets().getByIndex(0).getCellRangeByName(cell).setValue(value)
        calc.store()
    finally:
        calc.close(True)


def _link(path, sheet="Data", reference="A1:D3"):
    command = f"org.librecharts:LinkData?url={quote(str(path), safe='')}"
    if sheet:
        command += f"&sheet={quote(sheet, safe='')}"
    return command + f"&range={quote(reference, safe='')}"


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def _texts(group):
    texts = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.String:
            texts.append(child.String)
    return texts


def _undo_depth(doc):
    return len(doc.getUndoManager().getAllUndoActionTitles())


def _linked_chart(ctx, source):
    doc = new_impress(ctx)
    dispatch(ctx, doc, INSERT)  # selects the new chart
    group, chart_id = store.find_charts(first_page(doc))[0]
    dispatch(ctx, doc, _link(source))
    assert _state(doc, chart_id).link is not None, "linking failed"
    return doc, group, chart_id


def test_linking_takes_the_source_values_in_one_undo_step(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        depth = _undo_depth(doc)

        dispatch(ctx, doc, _link(source))

        state = _state(doc, chart_id)
        assert state.link is not None
        assert (state.link.sheet, state.link.range) == ("Data", "A1:D3")
        assert state.link.relative == ""  # the presentation was never saved
        assert state.link.updated
        assert state.link.modified
        assert state.cells[0] == ("", "2024", "2025", "2026")
        assert state.values[2][1:] == (20.0, 22.0, 21.0)
        assert "North" in _texts(group)
        assert _undo_depth(doc) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).link is None
        assert "North" not in _texts(group)
    finally:
        doc.close(True)


def test_an_update_reads_the_changed_source_in_one_undo_step(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    try:
        _change(ctx, source, "B2", 99)
        depth = _undo_depth(doc)

        dispatch(ctx, doc, "org.librecharts:UpdateLink")

        assert _state(doc, chart_id).values[1][1] == 99
        assert _undo_depth(doc) == depth + 1
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, chart_id).values[1][1] == 10
    finally:
        doc.close(True)


def test_update_all_links_updates_every_chart_in_one_undo_step(ctx):
    source = _workbook(ctx, _folder() / "sales.xlsx")
    doc, _, first_id = _linked_chart(ctx, source)
    try:
        dispatch(ctx, doc, INSERT)
        second_id = next(i for _, i in store.find_charts(first_page(doc)) if i != first_id)
        dispatch(ctx, doc, _link(source, reference="A1:D2"))
        assert _state(doc, second_id).values[1][1] == 10
        _change(ctx, source, "B2", 50)
        depth = _undo_depth(doc)

        dispatch(ctx, doc, "org.librecharts:UpdateAllLinks")

        assert _state(doc, first_id).values[1][1] == 50
        assert _state(doc, second_id).values[1][1] == 50
        assert len(_state(doc, second_id).values) == 2
        assert _undo_depth(doc) == depth + 1
        uno_command(ctx, doc, ".uno:Undo")
        assert _state(doc, first_id).values[1][1] == 10
        assert _state(doc, second_id).values[1][1] == 10
    finally:
        doc.close(True)


def test_a_missing_source_leaves_the_chart_unchanged(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    try:
        before = _state(doc, chart_id)
        source.unlink()
        depth = _undo_depth(doc)

        dispatch(ctx, doc, "org.librecharts:UpdateLink")

        assert _state(doc, chart_id) == before
        assert _undo_depth(doc) == depth
    finally:
        doc.close(True)


def test_a_named_range_and_a_csv_file_can_be_linked(ctx):
    folder = _folder()
    named = _workbook(ctx, folder / "named.ods", names=(("Revenue", "$Data.$A$1:$C$3"),))
    csv = folder / "regions.csv"
    csv.write_text("Region;2024;2025\nNorth;1;2\nSouth;3;4\n", encoding="utf-8")
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        _, chart_id = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, _link(named, sheet="", reference="Revenue"))
        state = _state(doc, chart_id)
        assert state.link is not None
        assert (state.link.sheet, state.link.range) == ("", "Revenue")
        assert state.cells[0] == ("", "2024", "2025")

        dispatch(ctx, doc, _link(csv, sheet="regions", reference="A1:C3"))
        state = _state(doc, chart_id)
        assert state.cells[1][0] == "North"
        assert state.values[2][1:] == (3.0, 4.0)
    finally:
        doc.close(True)


def test_moving_deck_and_workbook_together_keeps_the_link(ctx):
    root = _folder()
    old, new = root / "old", root / "new"
    (old / "data").mkdir(parents=True)
    source = _workbook(ctx, old / "data" / "sales.ods")
    doc = new_impress(ctx)
    try:
        doc.storeAsURL(_url(old / "deck.odp"), (prop("FilterName", "impress8"),))
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, _link(source))
        _, chart_id = store.find_charts(first_page(doc))[0]
        link = _state(doc, chart_id).link
        assert link is not None
        assert link.relative == "data/sales.ods"
        doc.store()
    finally:
        doc.close(True)
    shutil.copytree(old, new)
    shutil.rmtree(old)
    _change(ctx, new / "data" / "sales.ods", "B2", 7)

    moved = desktop(ctx).loadComponentFromURL(
        _url(new / "deck.odp"), "_blank", 0, (prop("Hidden", True),)
    )
    try:
        group, chart_id = store.find_charts(first_page(moved))[0]
        moved.getCurrentController().select(group)
        dispatch(ctx, moved, "org.librecharts:UpdateLink")
        state = _state(moved, chart_id)
        assert state.values[1][1] == 7
        assert state.link is not None
        assert same_file(state.link.url, _url(new / "data" / "sales.ods"))
    finally:
        moved.close(True)


def test_the_link_survives_odp_and_pptx(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    try:
        link = _state(doc, chart_id).link
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                ((group, reloaded_id),) = store.find_charts(first_page(reloaded))
                assert _state(reloaded, reloaded_id).link == link, fmt
                assert "North" in _texts(group), fmt
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)


def test_an_open_source_is_read_with_its_unsaved_edits_and_left_open(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    opened = None
    try:
        dispatch(ctx, doc, "org.librecharts:OpenSource")
        opened = links.open_document(ctx, _url(source))
        assert opened is not None, "the source was not opened"
        opened.getSheets().getByIndex(0).getCellRangeByName("C3").setValue(77)

        dispatch(ctx, doc, "org.librecharts:UpdateLink")

        assert _state(doc, chart_id).values[2][2] == 77
        assert links.open_document(ctx, _url(source)) is not None
    finally:
        if opened is not None:
            opened.close(True)
        doc.close(True)


def test_the_data_sheet_is_read_only_until_the_link_is_removed(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    try:
        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        sheet = calc.getSheets().getByIndex(0)
        assert sheet.isProtected()
        assert "sales.ods" in calc.getCurrentController().getFrame().Title
        assert sheet.getCellRangeByName("B1").getString() == "2024"
        assert sheet.getCellRangeByName("C3").getValue() == 22
        depth = _undo_depth(doc)

        dispatch(ctx, doc, "org.librecharts:RemoveLink")

        state = _state(doc, chart_id)
        assert state.link is None
        assert state.values[2][2] == 22
        assert _undo_depth(doc) == depth + 1
        assert not sheet.isProtected()
        assert not calc.isModified()
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_a_changed_source_is_detected_without_opening_it(ctx):
    source = _workbook(ctx, _folder() / "sales.ods")
    doc, _, chart_id = _linked_chart(ctx, source)
    try:
        assert links.changed_sources(ctx, doc) == []
        _change(ctx, source, "D3", 30)
        assert links.changed_sources(ctx, doc) == [chart_id]
        dispatch(ctx, doc, "org.librecharts:UpdateAllLinks")
        assert links.changed_sources(ctx, doc) == []
    finally:
        doc.close(True)


def test_opening_a_presentation_with_a_changed_source_offers_an_update(ctx):
    skip_on_headless_linux("visible documents abort LibreOffice in headless Linux")
    folder = _folder()
    source = _workbook(ctx, folder / "sales.ods")
    doc, _, _ = _linked_chart(ctx, source)
    deck = folder / "deck.odp"
    try:
        doc.storeToURL(_url(deck), (prop("FilterName", "impress8"),))
    finally:
        doc.close(True)
    _change(ctx, source, "B2", 1)
    reopened = desktop(ctx).loadComponentFromURL(_url(deck), "_blank", 0, ())
    try:
        controller = reopened.getCurrentController()
        deadline = time.monotonic() + 10
        while not controller.hasInfobar(links.INFOBAR):
            assert time.monotonic() < deadline, "no info bar offering the update"
            time.sleep(0.1)
        assert not reopened.isModified()  # the offer changes nothing by itself
    finally:
        reopened.close(True)
