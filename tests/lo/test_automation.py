# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The automation API and the build command in a real LibreOffice (M18, ADR 0028).

A template carries placeholder rectangles; the deck specification is written by the tests into a
temp folder. The launcher of the command line (``scripts/deck.py``) is tested by hand; its worker
is covered by ``test_cli.py``.
"""

import json
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from helpers import (
    deck_spec,
    deck_template,
    desktop,
    dispatch,
    first_page,
    new_impress,
    placeholder_rect,
    prop,
    url_of,
)

from librecharts import api
from librecharts.core import deck as core_deck
from librecharts.core.deck import DeckError
from librecharts.lo import chart, deck, links, render, store

DATA = [[None, "2023", "2024"], ["Product A", 10, 12], ["Product B", 20, 22]]
CALC_FILTERS = {"ods": "calc8"}


def _fails(call):
    """The ``DeckError`` that ``call`` raises; fails the test if it does not raise."""
    try:
        call()
    except DeckError as exc:
        return exc
    raise AssertionError("expected a DeckError")


def _folder():
    return Path(tempfile.mkdtemp(prefix="librecharts_deck_"))


def _chart(placeholder, **fields):
    return {"placeholder": placeholder, "kind": "column", "data": DATA, **fields}


def _load(ctx, path):
    return desktop(ctx).loadComponentFromURL(url_of(path), "_blank", 0, (prop("Hidden", True),))


def _boxes(doc):
    """The layout box of every chart of the document, by chart id."""
    found = {}
    for page in doc.getDrawPages():
        for group, chart_id in store.find_charts(page):
            found[chart_id] = render.layout_box(group)
    return found


def _build(ctx, template, spec, name="deck.odp"):
    out = _folder() / name
    parsed = core_deck.parse(spec.read_text("utf-8"), "en")
    return out, deck.build(ctx, str(template), parsed, str(out))


def _texts(group):
    return [group.getByIndex(index).String for index in range(group.getCount())]


def test_a_build_replaces_every_placeholder_at_its_box(ctx):
    template = deck_template(ctx, ["revenue", "costs"])
    spec = deck_spec([_chart("revenue"), _chart("costs", kind="bar")])
    out, report = _build(ctx, template, spec)
    assert "2 charts written to deck.odp" in report, report

    doc = _load(ctx, out)
    try:
        ((first, first_id), (_, second_id)) = store.find_charts(first_page(doc))
        assert _boxes(doc) == {
            first_id: (1000, 1000, 9000, 5000),
            second_id: (1000, 7000, 9000, 5000),
        }
        assert deck.placeholders(doc) == {}
        state = store.read_state(doc, second_id)
        assert state is not None
        assert (state.kind, state.values[1]) == ("bar", (None, 10.0, 12.0))
        assert "Product B" in _texts(first)
    finally:
        doc.close(True)


def test_a_chart_without_a_placeholder_is_refused_and_writes_nothing(ctx):
    template = deck_template(ctx, ["revenue"])
    spec = deck_spec([_chart("revenue"), _chart("costs")])
    out = _folder() / "deck.odp"
    parsed = core_deck.parse(spec.read_text("utf-8"), "en")
    error = _fails(lambda: deck.build(ctx, str(template), parsed, str(out)))
    assert error.key == "deck_missing_placeholders"
    assert "costs" in error.detail
    assert not out.exists()


def test_a_placeholder_without_a_chart_stays_and_is_reported(ctx):
    template = deck_template(ctx, ["revenue", "unused"])
    out, report = _build(ctx, template, deck_spec([_chart("revenue")]))
    assert "unused" in report
    doc = _load(ctx, out)
    try:
        assert list(deck.placeholders(doc)) == ["unused"]
        assert len(store.find_charts(first_page(doc))) == 1
    finally:
        doc.close(True)


def test_a_duplicated_placeholder_stops_the_build(ctx):
    template = deck_template(ctx, ["revenue", "revenue"])
    out = _folder() / "deck.odp"
    spec = core_deck.parse(deck_spec([_chart("revenue")]).read_text("utf-8"), "en")
    error = _fails(lambda: deck.build(ctx, str(template), spec, str(out)))
    assert error.key == "deck_duplicate_placeholders"
    assert not out.exists()


def test_the_template_keeps_its_slides_and_the_chart_lands_on_the_right_one(ctx):
    template = deck_template(ctx, ["revenue"], pages=2)
    out, _ = _build(ctx, template, deck_spec([_chart("revenue")]))
    doc = _load(ctx, out)
    try:
        assert doc.getDrawPages().getCount() == 2
        assert store.find_charts(doc.getDrawPages().getByIndex(0)) == []
        assert len(store.find_charts(doc.getDrawPages().getByIndex(1))) == 1
    finally:
        doc.close(True)


def test_a_too_small_placeholder_names_itself(ctx):
    doc = new_impress(ctx)
    try:
        placeholder_rect(doc, first_page(doc), "tiny", width=400, height=300)
        template = _folder() / "small.odp"
        doc.storeToURL(url_of(template), (prop("FilterName", "impress8"),))
    finally:
        doc.close(True)
    out = _folder() / "deck.odp"
    spec = core_deck.parse(deck_spec([_chart("tiny")]).read_text("utf-8"), "en")
    error = _fails(lambda: deck.build(ctx, str(template), spec, str(out)))
    assert (error.key, error.detail) == ("deck_placeholder_too_small", "tiny")


def test_a_deck_can_be_saved_as_pptx(ctx):
    template = deck_template(ctx, ["revenue"])
    out, report = _build(ctx, template, deck_spec([_chart("revenue")]), name="deck.pptx")
    assert "deck.pptx" in report
    doc = _load(ctx, out)
    try:
        assert len(store.find_charts(first_page(doc))) == 1
    finally:
        doc.close(True)


def test_an_unreadable_specification_is_a_deck_error(ctx):
    error = _fails(lambda: deck.read_spec(str(_folder() / "missing.json")))
    assert error.key == "deck_spec_unreadable"


def test_insert_chart_puts_one_chart_on_a_slide(ctx):
    doc = new_impress(ctx)
    try:
        chart_id = api.insert_chart(ctx, doc, 0, json.dumps({"kind": "pie", "data": DATA}), "en")
        assert chart_id
        state = store.read_state(doc, chart_id)
        assert state is not None
        assert state.kind == "pie"
        assert len(store.find_charts(first_page(doc))) == 1
    finally:
        doc.close(True)


def test_insert_chart_rejects_a_slide_that_does_not_exist(ctx):
    doc = new_impress(ctx)
    try:
        spec = json.dumps({"kind": "pie", "data": DATA})
        error = _fails(lambda: api.insert_chart(ctx, doc, 5, spec, "en"))
        assert error.key == "deck_bad_slide"
    finally:
        doc.close(True)


def _workbook(ctx, path, rows):
    calc = desktop(ctx).loadComponentFromURL(
        "private:factory/scalc", "_blank", 0, (prop("Hidden", True),)
    )
    try:
        sheet = calc.getSheets().getByIndex(0)
        sheet.setName("Data")  # the default name follows the UI language
        sheet.getCellRangeByPosition(0, 0, len(rows[0]) - 1, len(rows) - 1).setDataArray(rows)
        calc.storeToURL(url_of(path), (prop("FilterName", CALC_FILTERS["ods"]),))
    finally:
        calc.close(True)
    return path


def _change(ctx, path, cell, value):
    time.sleep(1.1)  # a new modification time, even on file systems with whole seconds
    calc = desktop(ctx).loadComponentFromURL(url_of(path), "_blank", 0, (prop("Hidden", True),))
    try:
        calc.getSheets().getByIndex(0).getCellRangeByName(cell).setValue(value)
        calc.store()
    finally:
        calc.close(True)


def test_update_links_refreshes_a_deck(ctx):
    folder = _folder()
    source = _workbook(ctx, folder / "sales.ods", (("", "2024", "2025"), ("North", 1.0, 2.0)))
    doc = new_impress(ctx)
    try:
        api.insert_chart(ctx, doc, 0, json.dumps({"kind": "column", "data": DATA}), "en")
        group, chart_id = store.find_charts(first_page(doc))[0]
        doc.getCurrentController().select(group)
        state = store.read_state(doc, chart_id)
        assert state is not None
        linked = links.link(ctx, doc, state, url_of(source), "Data", "A1:C2")
        chart.redraw(doc, group, linked)
        _change(ctx, source, "B2", 99)

        report = api.update_links(ctx, doc, None, "en")

        assert "1 of 1" in report, report
        updated = store.read_state(doc, chart_id)
        assert updated is not None
        assert updated.values[1][1] == 99
    finally:
        doc.close(True)


def _build_command(template, spec, out):
    """The macro command that builds a deck (``org.librecharts:BuildDeck``)."""
    encoded = [
        f"{name}={quote(url_of(value), safe='')}"
        for name, value in (("template", template), ("data", spec), ("out", out))
    ]
    return "org.librecharts:BuildDeck?" + "&".join(encoded)


def test_the_build_command_builds_a_deck(ctx):
    template = deck_template(ctx, ["revenue"])
    spec = deck_spec([_chart("revenue")])
    out = _folder() / "deck.odp"
    doc = _load(ctx, template)  # any presentation frame can dispatch the command
    try:
        dispatch(ctx, doc, _build_command(template, spec, out))
    finally:
        doc.close(True)
    assert out.exists()


def test_the_build_command_writes_nothing_when_a_placeholder_is_missing(ctx):
    template = deck_template(ctx, ["revenue"])
    spec = deck_spec([_chart("nowhere")])
    out = _folder() / "deck.odp"
    doc = _load(ctx, template)
    try:
        dispatch(ctx, doc, _build_command(template, spec, out))
    finally:
        doc.close(True)
    assert not out.exists()
