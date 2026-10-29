# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The agenda of a presentation: its main slide, dividers and their lists (ADR 0022).

``core/agenda.py`` decides what a command changes; this module finds the agenda slides, inserts
and removes slides and writes the lists. LibreOffice records neither slides inserted through the
API nor, with recording locked, removed ones. So every command is one explicit undo action that
re-applies the agenda as it was before or after the command (``_State``). It matches slides by
their role, never by page objects, which do not come back once a slide is removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import uno
from com.sun.star.awt import Point, Size

from librecharts.core import agenda as core
from librecharts.core.agenda import MAIN, Agenda, AgendaError, Line, Slide
from librecharts.core.messages import text
from librecharts.lo import scheme, store, undo

TITLE_ONLY = 19  # the slide layout "Title Only" (property Layout)
TITLE_SHAPE = "com.sun.star.presentation.TitleTextShape"
FONT_SIZE = 20.0  # pt, the list of a new agenda
GAP = 600  # 1/100 mm between the title and the list of a new agenda
INDENT = 1000  # 1/100 mm, the titles hang behind their numbers
SPACING = 250  # 1/100 mm below every chapter
BOLD = 150.0  # com.sun.star.awt.FontWeight.BOLD
NORMAL = 100.0  # com.sun.star.awt.FontWeight.NORMAL

_TOP = uno.Enum("com.sun.star.drawing.TextVerticalAdjust", "TOP")


class Refused(Exception):
    """A command cannot run; ``key`` is the message that tells the user why."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass(frozen=True, slots=True)
class _State:
    """The agenda before or after a command: the stored chapters (``None``: no property), the
    agenda slides, and the main list as the user left it (``None``: written from the chapters)."""

    agenda: Agenda | None
    slides: tuple[Slide, ...]
    main_text: tuple[str, ...] | None = None


def role_of_page(page: Any) -> str | None:
    """``MAIN`` or the chapter id if ``page`` is an agenda slide, else ``None``."""
    for i in range(page.getCount()):
        role = core.role(_name(page.getByIndex(i)))
        if role is not None:
            return role
    return None


def stored(doc: Any) -> bool:
    """Whether the presentation has an agenda; reads the property only (for the sidebar)."""
    return store.read_property(doc, store.AGENDA_PROPERTY) is not None


def insert(doc: Any, controller: Any, locale: str) -> None:
    """Insert the main agenda slide after the current slide and show it; one undo step."""
    found = _find(doc)
    if MAIN in found:
        raise Refused("agenda_exists")
    before = _State(_read(doc), _slides(found))
    placeholders = [
        text("agenda_placeholder", locale, number=str(number))
        for number in range(1, core.PLACEHOLDERS + 1)
    ]
    index = _index(doc, controller.getCurrentPage())
    outcome = core.insert_agenda(before.agenda, before.slides, index, placeholders)
    _run(doc, "Insert LibreCharts agenda", before, _State(outcome.agenda, outcome.slides), locale)
    controller.setCurrentPage(_find(doc)[MAIN][1])


def start_chapter(doc: Any, controller: Any, locale: str) -> None:
    """Insert a divider before the current slide and show it; one undo step.

    The divider starts the next chapter, or a new one (``core.start_chapter``).
    """
    found = _find(doc)
    if MAIN not in found:
        raise Refused("agenda_missing")
    page = controller.getCurrentPage()
    if role_of_page(page) is not None:
        raise Refused("agenda_on_agenda_slide")
    before, titles = _edited(doc, found)
    try:
        outcome, chapter = core.start_chapter(
            before.agenda or Agenda(),
            titles,
            before.slides,
            _index(doc, page),
            text("agenda_new_chapter", locale),
        )
    except AgendaError:
        raise Refused("agenda_first_slide") from None
    _run(doc, "Start LibreCharts chapter", before, _State(outcome.agenda, outcome.slides), locale)
    controller.setCurrentPage(_find(doc)[chapter][1])


def update(doc: Any, locale: str) -> None:
    """Take the chapters from the main slide's list and rewrite every divider; dividers of deleted
    chapters are removed. One undo step."""
    found = _find(doc)
    if MAIN not in found:
        raise Refused("agenda_missing")
    before, titles = _edited(doc, found)
    outcome = core.update(before.agenda or Agenda(), titles, before.slides)
    _run(doc, "Update LibreCharts agenda", before, _State(outcome.agenda, outcome.slides), locale)


def _edited(doc: Any, found: dict[str, tuple[int, Any, Any]]) -> tuple[_State, tuple[str, ...]]:
    """The state of an existing agenda before a command and the titles on its main slide."""
    typed = str(found[MAIN][2].String)
    titles = core.parse_titles(typed)
    if not titles:
        raise Refused("agenda_empty")
    return _State(_read(doc), _slides(found), tuple(typed.split("\n"))), titles


def _run(doc: Any, title: str, before: _State, after: _State, locale: str) -> None:
    _apply(doc, after, locale)
    undo.add_action(
        doc,
        title,
        undo=lambda: _apply(doc, before, locale),
        redo=lambda: _apply(doc, after, locale),
    )


def _apply(doc: Any, state: _State, locale: str) -> None:
    """Bring the property, the agenda slides and their lists to ``state``."""
    with undo.recording_locked(doc):
        if state.agenda is None:
            store.remove_property(doc, store.AGENDA_PROPERTY)
        else:
            store.write_property(doc, store.AGENDA_PROPERTY, core.to_json(state.agenda))
        pages = doc.getDrawPages()
        remove, insert = core.changes(_slides(_find(doc)), state.slides)
        for index in remove:
            pages.remove(pages.getByIndex(index))
        for slide in insert:
            page = pages.insertNewByIndex(slide.index - 1)  # inserts after the given index
            if slide.role == MAIN:
                _new_main(doc, page, locale)
            else:
                _new_list(doc, page, slide.role)
        if state.agenda is not None:
            _draw(doc, state, {slide.role for slide in insert})


def _new_main(doc: Any, page: Any, locale: str) -> None:
    """A title and an empty list below it on the new main slide ``page``."""
    page.Layout = TITLE_ONLY
    shape = _new_list(doc, page, MAIN)
    title = _title(page)
    if title is not None:
        title.String = text("agenda_title", locale)
        left, top = title.Position.X, title.Position.Y + title.Size.Height + GAP
        width, height = title.Size.Width, page.Height - top - title.Position.Y
    else:  # a master without a title placeholder
        left = top = GAP
        width, height = page.Width - 2 * GAP, page.Height - 2 * GAP
    shape.Position = Point(left, top)
    shape.Size = Size(width, max(height, GAP))
    shape.CharHeight = FONT_SIZE


def _new_list(doc: Any, page: Any, role: str) -> Any:
    shape = doc.createInstance("com.sun.star.drawing.TextShape")
    page.add(shape)
    shape.Name = core.shape_name(role)
    shape.TextAutoGrowHeight = False
    shape.TextVerticalAdjust = _TOP
    return shape


def _draw(doc: Any, state: _State, new_roles: set[str]) -> None:
    """Write the lists of the main slide and the dividers of ``state``; new dividers take the
    master and layout of the main slide, every divider its title, list position and font."""
    found = _find(doc)
    if MAIN not in found or state.agenda is None:
        return
    _, main_page, main_list = found[MAIN]
    colours = scheme.load(doc)
    font = _font(main_list)
    if state.main_text is None:
        main_lines = core.lines(state.agenda, colours)
    else:
        main_lines = tuple(Line(paragraph, colours.text) for paragraph in state.main_text)
    _write(main_list, main_lines, font)
    title = _title(main_page)
    for chapter_id in state.agenda.ids():
        if chapter_id not in found:
            continue
        _, page, shape = found[chapter_id]
        if chapter_id in new_roles:
            page.MasterPage = main_page.MasterPage
            page.Layout = main_page.Layout
        divider_title = _title(page)
        if title is not None and divider_title is not None:
            divider_title.String = title.String
        shape.Position = main_list.Position
        shape.Size = main_list.Size
        _write(shape, core.lines(state.agenda, colours, chapter_id), font)


def _write(shape: Any, lines: tuple[Line, ...], font: tuple[str, float]) -> None:
    name, size = font
    shape.String = "\n".join(line.text for line in lines)
    body = shape.getText()
    for paragraph, line in zip(_paragraphs(shape), lines, strict=False):
        # Character attributes through a cursor: set on the paragraph, they lose against the
        # attributes of its text, which the new text took over from a reloaded document.
        characters = body.createTextCursorByRange(paragraph)
        characters.CharFontName = name
        characters.CharHeight = size
        characters.CharColor = line.color
        characters.CharWeight = BOLD if line.bold else NORMAL
        paragraph.ParaLeftMargin = INDENT
        paragraph.ParaFirstLineIndent = -INDENT
        paragraph.ParaBottomMargin = SPACING


def _font(shape: Any) -> tuple[str, float]:
    """The font at the start of the list, which every list takes over.

    Read from the first text portion: after reloading, a paragraph reports its style's font.
    """
    first = shape
    paragraphs = _paragraphs(shape)
    if paragraphs:
        portions = paragraphs[0].createEnumeration()
        first = portions.nextElement() if portions.hasMoreElements() else paragraphs[0]
    return str(first.CharFontName), float(first.CharHeight)


def _paragraphs(shape: Any) -> list[Any]:
    paragraphs: list[Any] = []
    enumeration = shape.getText().createEnumeration()
    while enumeration.hasMoreElements():
        paragraphs.append(enumeration.nextElement())
    return paragraphs


def _title(page: Any) -> Any:
    """The title placeholder of ``page``, or ``None``."""
    for i in range(page.getCount()):
        shape = page.getByIndex(i)
        if shape.ShapeType == TITLE_SHAPE:
            return shape
    return None


def _find(doc: Any) -> dict[str, tuple[int, Any, Any]]:
    """The agenda slides by role: page index, page and list shape (the first slide of a role)."""
    pages = doc.getDrawPages()
    found: dict[str, tuple[int, Any, Any]] = {}
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for i in range(page.getCount()):
            shape = page.getByIndex(i)
            role = core.role(_name(shape))
            if role is not None:
                found.setdefault(role, (index, page, shape))
                break
    return found


def _slides(found: dict[str, tuple[int, Any, Any]]) -> tuple[Slide, ...]:
    slides = (Slide(index, role) for role, (index, _, _) in found.items())
    return tuple(sorted(slides, key=lambda slide: slide.index))


def _index(doc: Any, page: Any) -> int:
    pages = doc.getDrawPages()
    return next(i for i in range(pages.getCount()) if pages.getByIndex(i) == page)


def _read(doc: Any) -> Agenda | None:
    """The stored agenda; ``None`` if there is none or it cannot be read."""
    stored_text = store.read_property(doc, store.AGENDA_PROPERTY)
    if stored_text is None:
        return None
    try:
        return core.from_json(stored_text)
    except AgendaError:
        return None


def _name(shape: Any) -> str:
    return str(getattr(shape, "Name", ""))
