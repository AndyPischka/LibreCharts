# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Corporate design check in a real LibreOffice (M19, ADR 0029)."""

import json
import tempfile
from pathlib import Path

import uno
from helpers import dispatch, first_page, new_impress, uno_command

from librecharts import api
from librecharts.core import style
from librecharts.core.designcheck import Margins, Rules, rules_to_json
from librecharts.lo import render, scheme, store

INSERT = "org.librecharts:InsertColumnChart"
CORPORATE = style.Scheme("Corporate", (0x003366, 0xFF9900, 0x99CCFF), font_name="DejaVu Sans")
RULES = Rules(CORPORATE, margins=Margins(1000, 1000, 1000, 1000))


def _design_file(rules=RULES):
    path = Path(tempfile.mkdtemp(prefix="librecharts_")) / "corporate.json"
    path.write_text(rules_to_json(rules), encoding="utf-8")
    return path


def _rectangle(doc, page, x, y, fill):
    shape = doc.createInstance("com.sun.star.drawing.RectangleShape")
    page.add(shape)
    shape.Position = uno.createUnoStruct("com.sun.star.awt.Point", x, y)
    shape.Size = uno.createUnoStruct("com.sun.star.awt.Size", 4000, 2000)
    shape.FillColor = fill
    shape.LineStyle = uno.Enum("com.sun.star.drawing.LineStyle", "NONE")
    shape.Name = "Box"
    return shape


def _text_box(doc, page, font):
    shape = doc.createInstance("com.sun.star.drawing.TextShape")
    page.add(shape)
    shape.Position = uno.createUnoStruct("com.sun.star.awt.Point", 2000, 12000)
    shape.Size = uno.createUnoStruct("com.sun.star.awt.Size", 8000, 1500)
    shape.String = "Quarterly figures"
    cursor = shape.getText().createTextCursor()
    cursor.gotoEnd(True)
    cursor.CharFontName = font
    return shape


def _font(shape):
    paragraph = shape.getText().createEnumeration().nextElement()
    return paragraph.createEnumeration().nextElement().CharFontName


def test_a_check_finds_colours_fonts_positions_and_the_scheme_without_changing_anything(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        page = first_page(doc)
        box = _rectangle(doc, page, -1500, 2000, 0x123456)
        text = _text_box(doc, page, "Liberation Serif")

        result = api.check_design(doc, str(_design_file()))

        issues = sorted(finding.issue for finding in result.findings)
        assert issues == ["fill", "font", "position", "scheme"], issues
        assert box.FillColor == 0x123456
        assert box.Position.X == -1500
        assert _font(text) == "Liberation Serif"
        assert scheme.load(doc) == style.DEFAULT
    finally:
        doc.close(True)


def test_fixing_corrects_every_deviation_as_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        page = first_page(doc)
        group, _ = store.find_charts(page)[0]
        box = _rectangle(doc, page, -1500, 2000, 0x123456)
        text = _text_box(doc, page, "Liberation Serif")
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())
        location = uno.systemPathToFileUrl(str(_design_file()))

        dispatch(ctx, doc, f"org.librecharts:CheckDesign?file={location}&fix=true")

        assert box.FillColor == 0x003366
        assert box.Position.X == 1000
        assert _font(text) == "DejaVu Sans"
        assert scheme.load(doc).palette == CORPORATE.palette
        assert len(manager.getAllUndoActionTitles()) == depth + 1
        assert api.check_design(doc, location).clean

        uno_command(ctx, doc, ".uno:Undo")

        assert box.FillColor == 0x123456
        assert box.Position.X == -1500
        assert _font(text) == "Liberation Serif"
        assert scheme.load(doc) == style.DEFAULT
        assert store.chart_id_of(group) is not None
    finally:
        doc.close(True)


def test_a_chart_outside_the_margins_is_moved_by_its_frame(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        page = first_page(doc)
        group, _ = store.find_charts(page)[0]
        _, y, width, height = render.layout_box(group)
        group.Position = uno.createUnoStruct("com.sun.star.awt.Point", -2000, y)
        rules = Rules(style.DEFAULT, margins=Margins(500, 0, 500, 0))

        api.check_design(doc, str(_design_file(rules)), fix=True)

        x, _, new_width, new_height = render.layout_box(group)
        assert x == 500
        assert (new_width, new_height) == (width, height)
    finally:
        doc.close(True)


def test_an_unreadable_design_file_changes_nothing(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        path = Path(tempfile.mkdtemp(prefix="librecharts_")) / "broken.json"
        path.write_text(json.dumps({"palette": "red"}), encoding="utf-8")
        depth = len(doc.getUndoManager().getAllUndoActionTitles())

        dispatch(ctx, doc, f"org.librecharts:CheckDesign?file={uno.systemPathToFileUrl(str(path))}")

        assert len(doc.getUndoManager().getAllUndoActionTitles()) == depth
        assert scheme.load(doc) == style.DEFAULT
    finally:
        doc.close(True)
