# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The command line's worker in a real LibreOffice (M18, ADR 0028).

``scripts/deck.py`` finds LibreOffice and starts a headless one for the job; here the worker runs
against the LibreOffice the test runner is connected to, so only the process handling is untested.
"""

import json
import tempfile
import time
from pathlib import Path

from helpers import (
    deck_spec,
    deck_template,
    desktop,
    first_page,
    new_impress,
    prop,
    url_of,
)

from librecharts import api
from librecharts.core import cli as core_cli
from librecharts.lo import chart, links, store, worker

DATA = [[None, "2023", "2024"], ["Product A", 10, 12], ["Product B", 20, 22]]


def _args(*argv):
    """The arguments ``scripts/deck.py`` hands to the worker (the pipe is only for ``main``)."""
    return core_cli.parser().parse_args(["--pipe", "unused", *argv])


def test_build_writes_the_deck(ctx):
    template = deck_template(ctx, ["revenue"])
    spec = deck_spec([{"placeholder": "revenue", "kind": "pie", "data": DATA}])
    out = Path(tempfile.mkdtemp(prefix="librecharts_cli_")) / "deck.odp"

    code = worker.run(
        ctx, _args("build", "--template", str(template), "--data", str(spec), "--out", str(out))
    )

    assert code == 0
    assert out.exists()
    doc = desktop(ctx).loadComponentFromURL(url_of(out), "_blank", 0, (prop("Hidden", True),))
    try:
        ((_, chart_id),) = store.find_charts(first_page(doc))
        state = store.read_state(doc, chart_id)
        assert state is not None
        assert state.kind == "pie"
    finally:
        doc.close(True)


def test_a_broken_specification_returns_one_and_writes_nothing(ctx):
    template = deck_template(ctx, ["revenue"])
    spec = deck_spec([{"placeholder": "nowhere", "kind": "pie", "data": DATA}])
    out = Path(tempfile.mkdtemp(prefix="librecharts_cli_")) / "deck.odp"

    code = worker.run(
        ctx, _args("build", "--template", str(template), "--data", str(spec), "--out", str(out))
    )

    assert code == 1
    assert not out.exists()


def test_update_saves_the_deck_in_place(ctx):
    folder = Path(tempfile.mkdtemp(prefix="librecharts_cli_"))
    source = _workbook(ctx, folder / "sales.ods", (("", "2024", "2025"), ("North", 1.0, 2.0)))
    deck_path, chart_id = _linked_deck(ctx, folder, source)
    _change(ctx, source, "B2", 99)

    code = worker.run(ctx, _args("update", str(deck_path), "--locale", "en"))

    assert code == 0
    doc = desktop(ctx).loadComponentFromURL(url_of(deck_path), "_blank", 0, (prop("Hidden", True),))
    try:
        state = store.read_state(doc, chart_id)
        assert state is not None
        assert state.values[1][1] == 99
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
        calc.storeToURL(url_of(path), (prop("FilterName", "calc8"),))
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


def _linked_deck(ctx, folder, source):
    """A saved deck with one chart linked to ``source``; returns the deck's path and chart id."""
    doc = new_impress(ctx)
    try:
        api.insert_chart(ctx, doc, 0, json.dumps({"kind": "column", "data": DATA}), "en")
        group, chart_id = store.find_charts(first_page(doc))[0]
        doc.getCurrentController().select(group)
        state = store.read_state(doc, chart_id)
        assert state is not None
        linked = links.link(ctx, doc, state, url_of(source), "Data", "A1:C2")
        chart.redraw(doc, group, linked)
        path = folder / "deck.odp"
        doc.storeToURL(url_of(path), (prop("FilterName", "impress8"),))
    finally:
        doc.close(True)
    return path, chart_id
