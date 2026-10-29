# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The agenda in a real LibreOffice: main slide, dividers, update and undo (ADR 0022)."""

from helpers import dispatch, new_impress, save_and_reload, uno_command

from librecharts.core import agenda as core
from librecharts.core import style
from librecharts.core.messages import text
from librecharts.lo import agenda, ui

INSERT = "org.librecharts:InsertAgenda"
START = "org.librecharts:StartChapter"
UPDATE = "org.librecharts:UpdateAgenda"


def _deck(ctx, count):
    """A hidden presentation of ``count`` slides, each with a text box "Slide <n>"."""
    doc = new_impress(ctx)
    pages = doc.getDrawPages()
    while pages.getCount() < count:
        pages.insertNewByIndex(pages.getCount() - 1)
    for index in range(count):
        page = pages.getByIndex(index)
        box = doc.createInstance("com.sun.star.drawing.TextShape")
        page.add(box)
        box.String = f"Slide {index + 1}"
    return doc


def _go(doc, label):
    """Make the slide ``label`` ("Slide 3", "agenda") the current one."""
    index = _outline(doc).index(label)
    doc.getCurrentController().setCurrentPage(doc.getDrawPages().getByIndex(index))


def _outline(doc):
    """Every slide in order: "Slide <n>", "agenda" or "divider <highlighted title>"."""
    pages = doc.getDrawPages()
    outline = []
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        entry = "?"
        for i in range(page.getCount()):
            shape = page.getByIndex(i)
            role = core.role(shape.Name)
            if role == core.MAIN:
                entry = "agenda"
                break
            if role is not None:
                entry = "divider " + _highlighted(shape)
                break
            if shape.String.startswith("Slide "):
                entry = shape.String
        outline.append(entry)
    return outline


def _list(doc, role=core.MAIN):
    """The list shape of the agenda slide with ``role``."""
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for i in range(page.getCount()):
            shape = page.getByIndex(i)
            if core.role(shape.Name) == role:
                return shape
    raise AssertionError(f"no agenda list {role!r}")


def _paragraphs(shape):
    """(text, bold, colour) of every paragraph of a list, read from its first text portion:
    after reloading, the paragraph itself reports its style."""
    found = []
    enumeration = shape.getText().createEnumeration()
    while enumeration.hasMoreElements():
        paragraph = enumeration.nextElement()
        portion = paragraph.createEnumeration().nextElement()
        found.append((paragraph.getString(), portion.CharWeight > 100, portion.CharColor))
    return found


def _highlighted(shape):
    bold = [line for line, is_bold, _ in _paragraphs(shape) if is_bold]
    return ",".join(core.parse_titles("\n".join(bold)))


def _titles(doc):
    return core.parse_titles(_list(doc).String)


def _undo_depth(doc):
    return len(doc.getUndoManager().getAllUndoActionTitles())


def _with_two_chapters(ctx):
    """Slides 1-5, the agenda after slide 1, chapters starting at slides 2 and 4."""
    doc = _deck(ctx, 5)
    _go(doc, "Slide 1")
    dispatch(ctx, doc, INSERT)
    _go(doc, "Slide 2")
    dispatch(ctx, doc, START)
    _go(doc, "Slide 4")
    dispatch(ctx, doc, START)
    return doc


def test_insert_agenda_adds_a_main_slide_after_the_current_one_in_one_undo_step(ctx):
    doc = _deck(ctx, 3)
    try:
        _go(doc, "Slide 1")
        depth = _undo_depth(doc)

        dispatch(ctx, doc, INSERT)

        assert _outline(doc) == ["Slide 1", "agenda", "Slide 2", "Slide 3"]
        current = doc.getCurrentController().getCurrentPage()
        assert agenda.role_of_page(current) == core.MAIN
        locale = ui.ui_locale(ctx)
        placeholders = [text("agenda_placeholder", locale, number=str(n)) for n in (1, 2, 3)]
        assert [line for line, _, _ in _paragraphs(_list(doc))] == [
            f"{n}\t{title}" for n, title in enumerate(placeholders, 1)
        ]
        titles = [current.getByIndex(i).String for i in range(current.getCount())]
        assert text("agenda_title", locale) in titles
        assert agenda.stored(doc)
        assert _undo_depth(doc) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")
        assert _outline(doc) == ["Slide 1", "Slide 2", "Slide 3"]
        assert not agenda.stored(doc)

        uno_command(ctx, doc, ".uno:Redo")
        assert _outline(doc) == ["Slide 1", "agenda", "Slide 2", "Slide 3"]
        assert _titles(doc) == tuple(placeholders)
    finally:
        doc.close(True)


def test_dividers_start_the_chapters_and_highlight_them(ctx):
    doc = _with_two_chapters(ctx)
    try:
        first, second, third = _titles(doc)
        assert _outline(doc) == [
            "Slide 1",
            "agenda",
            f"divider {first}",
            "Slide 2",
            "Slide 3",
            f"divider {second}",
            "Slide 4",
            "Slide 5",
        ]
        current = doc.getCurrentController().getCurrentPage()
        role = agenda.role_of_page(current)
        assert role not in (None, core.MAIN)
        assert role is not None

        lines = _paragraphs(_list(doc, role))
        muted = style.mix(style.TEXT_COLOR, style.WHITE, core.MUTED_SHARE)
        assert lines == [
            (f"1\t{first}", False, muted),
            (f"2\t{second}", True, core.accent(style.DEFAULT)),
            (f"3\t{third}", False, muted),
        ]
        main, divider = _list(doc), _list(doc, role)
        assert (divider.Position.X, divider.Position.Y) == (main.Position.X, main.Position.Y)
        assert (divider.Size.Width, divider.Size.Height) == (main.Size.Width, main.Size.Height)
        assert current.Layout == agenda.TITLE_ONLY
        assert text("agenda_title", ui.ui_locale(ctx)) in [
            current.getByIndex(i).String for i in range(current.getCount())
        ]

        depth = _undo_depth(doc)
        uno_command(ctx, doc, ".uno:Undo")
        assert _outline(doc)[5] == "Slide 4"
        assert _undo_depth(doc) == depth - 1
    finally:
        doc.close(True)


def test_update_follows_the_edited_main_list_in_one_undo_step(ctx):
    doc = _with_two_chapters(ctx)
    try:
        third = _titles(doc)[2]
        edited = f"Intro\n{third}"
        _list(doc).String = edited  # renames chapter 1, deletes chapter 2
        depth = _undo_depth(doc)

        dispatch(ctx, doc, UPDATE)

        assert _outline(doc) == [
            "Slide 1",
            "agenda",
            "divider Intro",
            "Slide 2",
            "Slide 3",
            "Slide 4",
            "Slide 5",
        ]
        assert [line for line, _, _ in _paragraphs(_list(doc))] == ["1\tIntro", f"2\t{third}"]
        assert _undo_depth(doc) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")
        assert _outline(doc)[5].startswith("divider ")
        assert _outline(doc)[6] == "Slide 4"
        assert _list(doc).String == edited

        uno_command(ctx, doc, ".uno:Redo")
        assert "Slide 4" in _outline(doc)
        assert _outline(doc)[5] == "Slide 4"
        assert _titles(doc) == ("Intro", third)
    finally:
        doc.close(True)


def test_a_chapter_started_between_two_others_is_new(ctx):
    doc = _with_two_chapters(ctx)
    try:
        _go(doc, "Slide 3")
        dispatch(ctx, doc, START)

        titles = _titles(doc)
        assert len(titles) == 4
        assert titles[1] == text("agenda_new_chapter", ui.ui_locale(ctx))
        assert _outline(doc) == [
            "Slide 1",
            "agenda",
            f"divider {titles[0]}",
            "Slide 2",
            f"divider {titles[1]}",
            "Slide 3",
            f"divider {titles[2]}",
            "Slide 4",
            "Slide 5",
        ]
    finally:
        doc.close(True)


def test_commands_that_cannot_run_change_nothing(ctx):
    doc = _deck(ctx, 3)
    try:
        _go(doc, "Slide 2")
        dispatch(ctx, doc, START)  # no agenda yet
        dispatch(ctx, doc, UPDATE)
        assert _outline(doc) == ["Slide 1", "Slide 2", "Slide 3"]

        dispatch(ctx, doc, INSERT)
        _go(doc, "Slide 2")
        dispatch(ctx, doc, INSERT)  # a second agenda
        _go(doc, "agenda")
        dispatch(ctx, doc, START)  # on the agenda slide
        _go(doc, "Slide 1")
        dispatch(ctx, doc, START)  # on the first slide
        _list(doc).String = "\n"
        dispatch(ctx, doc, UPDATE)  # no chapters
        assert _outline(doc) == ["Slide 1", "Slide 2", "agenda", "Slide 3"]
    finally:
        doc.close(True)


def test_the_agenda_survives_odp_and_pptx(ctx):
    doc = _with_two_chapters(ctx)
    try:
        before = _outline(doc)
        for fmt in ("odp", "pptx"):
            again = save_and_reload(ctx, doc, fmt)
            try:
                assert _outline(again) == before, (fmt, _outline(again), before)
                assert agenda.stored(again), fmt
                titles = _titles(again)
                _list(again).String = "\n".join(("Renamed", *titles[1:]))

                dispatch(ctx, again, UPDATE)

                assert _outline(again)[2] == "divider Renamed", (fmt, _outline(again))
                assert _outline(again)[5] == f"divider {titles[1]}", fmt
            finally:
                again.close(True)
    finally:
        doc.close(True)
