"""The agenda: its chapters, the slides that show them and what a command changes (ADR 0022).

An agenda is a *main slide* listing the chapters and, before every chapter, a *divider*: a slide
with the same list and that chapter highlighted. Impress has no slide ids that survive PPTX and
cannot move slides through the API, so:

- agenda slides are found by the name of their list shape: ``librecharts-agenda`` on the main
  slide, ``librecharts-agenda:<chapter id>`` on a divider (only exact names; a slide the user
  duplicates gets a renamed copy and is left alone);
- a divider is where its chapter starts; LibreCharts never moves slides, the user moves a chapter
  with its divider in the slide sorter;
- the titles are edited on the main slide, one paragraph per chapter, and stored with their
  chapter ids as JSON in the document property ``librecharts:agenda``.

Pure Python, no UNO: ``lo/agenda.py`` finds the agenda slides, asks this module what to change
and carries it out.
"""

from __future__ import annotations

import json
import re
import uuid
from bisect import bisect_left
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast

from librecharts.core import style

MAIN_NAME = "librecharts-agenda"
MAIN = ""  # the role of the main slide; a divider's role is its chapter id
AGENDA_VERSION = 1
PLACEHOLDERS = 3  # chapters of a new agenda
MUTED_SHARE = 0.5  # how far the other chapters on a divider fade towards the background
MIN_CONTRAST = 3.0  # WCAG contrast ratio for large text; a weaker palette colour is no accent

_ID = re.compile(r"[0-9a-f]{12}")
_DIVIDER = re.compile(re.escape(MAIN_NAME) + r":(?P<id>[0-9a-f]{12})")
# The number LibreCharts writes in front of a title ("1<tab>"), or one typed as "1." or "1)".
_NUMBER = re.compile(r"\d+[.)]?\t\s*|\d+[.)]\s+")


class AgendaError(ValueError):
    """The stored agenda is malformed or from a newer LibreCharts, or a command cannot run."""


@dataclass(frozen=True, slots=True)
class Chapter:
    id: str
    title: str


@dataclass(frozen=True, slots=True)
class Agenda:
    """The chapters in the order of the main slide's list."""

    chapters: tuple[Chapter, ...] = ()

    def ids(self) -> tuple[str, ...]:
        return tuple(chapter.id for chapter in self.chapters)


@dataclass(frozen=True, slots=True)
class Slide:
    """An agenda slide: its page index in the presentation and its role (``MAIN`` or the id of
    the chapter it starts)."""

    index: int
    role: str


@dataclass(frozen=True, slots=True)
class Outcome:
    """The agenda and its slides (ascending by index) after a command."""

    agenda: Agenda
    slides: tuple[Slide, ...]


@dataclass(frozen=True, slots=True)
class Line:
    """One paragraph of an agenda list."""

    text: str
    color: int
    bold: bool = False


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def shape_name(role: str) -> str:
    """The name of the list shape of an agenda slide with ``role``."""
    return MAIN_NAME if role == MAIN else f"{MAIN_NAME}:{role}"


def role(name: str) -> str | None:
    """``MAIN`` for the main slide's list, the chapter id for a divider's, else ``None``."""
    if name == MAIN_NAME:
        return MAIN
    match = _DIVIDER.fullmatch(name)
    return None if match is None else match["id"]


def parse_titles(text: str) -> tuple[str, ...]:
    """The chapter titles in the text of the main slide's list: one per non-empty paragraph,
    without the number in front."""
    titles: list[str] = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        title = paragraph.strip()
        number = _NUMBER.match(title)
        if number is not None:
            title = title[number.end() :].strip()
        if title:
            titles.append(title)
    return tuple(titles)


def reconcile(agenda: Agenda, titles: Sequence[str], make_id: Callable[[], str] = new_id) -> Agenda:
    """The chapters after the main slide's list was edited to ``titles``.

    A title that is still there keeps its chapter, also if it moved. The other titles take over
    the remaining chapters in order (renamed ones), further titles become new chapters, and
    chapters left over were deleted.
    """
    unused = list(agenda.chapters)
    kept: list[Chapter | None] = []
    for title in titles:
        chapter = next((c for c in unused if c.title == title), None)
        if chapter is not None:
            unused.remove(chapter)
        kept.append(chapter)
    chapters: list[Chapter] = []
    for title, chapter in zip(titles, kept, strict=True):
        if chapter is None:
            chapter = Chapter(unused.pop(0).id if unused else make_id(), title)
        chapters.append(chapter)
    return Agenda(tuple(chapters))


def insert_agenda(
    agenda: Agenda | None,
    slides: Sequence[Slide],
    index: int,
    placeholders: Sequence[str],
    make_id: Callable[[], str] = new_id,
) -> Outcome:
    """The command "Insert agenda" after the slide at page ``index``: a main slide listing the
    stored chapters (whose main slide was deleted) or new chapters titled ``placeholders``."""
    if any(slide.role == MAIN for slide in slides):
        raise AgendaError("the presentation already has an agenda")
    if agenda is None or not agenda.chapters:
        agenda = Agenda(tuple(Chapter(make_id(), title) for title in placeholders))
    return Outcome(agenda, _with(slides, Slide(index + 1, MAIN)))


def update(
    agenda: Agenda,
    titles: Sequence[str],
    slides: Sequence[Slide],
    make_id: Callable[[], str] = new_id,
) -> Outcome:
    """The command "Update agenda": the chapters of ``titles``; the dividers of deleted chapters go.

    Dividers of chapters the stored agenda does not know (e.g. it was lost) stay as they are.
    """
    if not titles:
        raise AgendaError("an agenda needs at least one chapter")
    updated = reconcile(agenda, titles, make_id)
    deleted = set(agenda.ids()) - set(updated.ids())
    return Outcome(updated, _without(slides, deleted))


def start_chapter(
    agenda: Agenda,
    titles: Sequence[str],
    slides: Sequence[Slide],
    index: int,
    title: str,
    make_id: Callable[[], str] = new_id,
) -> tuple[Outcome, str]:
    """The command "Start chapter here" on the slide at page ``index``, which is no agenda slide:
    the update, then a divider before that slide. Returns the outcome and the divider's chapter.

    The divider starts the chapter after the one of the previous divider (the first, if there is
    none). If that chapter has a divider already, a new chapter ``title`` is inserted there.
    """
    updated = update(agenda, titles, slides, make_id)
    roles = {slide.role for slide in updated.slides}
    at = index - sum(1 for s in slides if s.role not in roles and s.index < index)
    if at < 1:
        raise AgendaError("a chapter cannot start on the first slide")
    ids = updated.agenda.ids()
    previous = [slide.role for slide in updated.slides if slide.index < at and slide.role in ids]
    position = ids.index(previous[-1]) + 1 if previous else 0
    chapters = list(updated.agenda.chapters)
    if position < len(chapters) and chapters[position].id not in roles:
        chapter_id = chapters[position].id
    else:
        chapter_id = make_id()
        chapters.insert(position, Chapter(chapter_id, title))
    outcome = Outcome(Agenda(tuple(chapters)), _with(updated.slides, Slide(at, chapter_id)))
    return outcome, chapter_id


def changes(
    current: Sequence[Slide], target: Sequence[Slide]
) -> tuple[tuple[int, ...], tuple[Slide, ...]]:
    """What turns the agenda slides ``current`` into ``target``: the page indices to remove
    (descending, so each stays valid) and the slides to insert (ascending, each at its index).
    A role in both keeps its slide where it is."""
    wanted = {slide.role for slide in target}
    present = {slide.role for slide in current}
    remove = sorted((s.index for s in current if s.role not in wanted), reverse=True)
    insert = sorted((s for s in target if s.role not in present), key=lambda s: s.index)
    return tuple(remove), tuple(insert)


def lines(agenda: Agenda, scheme: style.Scheme, current: str = MAIN) -> tuple[Line, ...]:
    """The numbered list of the main slide, or of the divider of chapter ``current``: its title
    bold in the accent colour, the others muted."""
    if current == MAIN:
        return tuple(
            Line(f"{number}\t{chapter.title}", scheme.text)
            for number, chapter in enumerate(agenda.chapters, 1)
        )
    highlight, muted = accent(scheme), style.mix(scheme.text, scheme.background, MUTED_SHARE)
    return tuple(
        Line(f"{number}\t{chapter.title}", highlight, bold=True)
        if chapter.id == current
        else Line(f"{number}\t{chapter.title}", muted)
        for number, chapter in enumerate(agenda.chapters, 1)
    )


def accent(scheme: style.Scheme) -> int:
    """The palette colour that stands out most against the background; the text colour if none
    is readable as large text."""
    best = max(scheme.palette, key=lambda colour: _contrast(colour, scheme.background))
    return best if _contrast(best, scheme.background) >= MIN_CONTRAST else scheme.text


def _contrast(first: int, second: int) -> float:
    darker, lighter = sorted((style.luminance(first), style.luminance(second)))
    return (lighter + 0.05) / (darker + 0.05)


def _with(slides: Sequence[Slide], new: Slide) -> tuple[Slide, ...]:
    """``slides`` after inserting ``new`` at its index: the slides from there on move down."""
    moved = [Slide(s.index + 1, s.role) if s.index >= new.index else s for s in slides]
    return tuple(sorted((*moved, new), key=lambda s: s.index))


def _without(slides: Sequence[Slide], roles: set[str]) -> tuple[Slide, ...]:
    """``slides`` after removing the slides of ``roles``: the slides after them move up."""
    removed = sorted(s.index for s in slides if s.role in roles)
    return tuple(
        Slide(s.index - bisect_left(removed, s.index), s.role)
        for s in sorted(slides, key=lambda s: s.index)
        if s.role not in roles
    )


def to_json(agenda: Agenda) -> str:
    """Serialize ``agenda`` for the document property."""
    return json.dumps(
        {
            "v": AGENDA_VERSION,
            "chapters": [{"id": c.id, "title": c.title} for c in agenda.chapters],
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def from_json(text: str) -> Agenda:
    """Parse an agenda written by :func:`to_json`; ``AgendaError`` if it is malformed or newer."""
    try:
        raw: object = json.loads(text)
    except ValueError as exc:
        raise AgendaError(f"invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise AgendaError("an agenda must be a JSON object")
    data = cast("dict[str, object]", raw)
    version = data.get("v")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise AgendaError("missing or invalid agenda version 'v'")
    if version > AGENDA_VERSION:
        raise AgendaError(
            f"agenda saved by a newer LibreCharts (version {version}, supported {AGENDA_VERSION})"
        )
    items = data.get("chapters")
    if not isinstance(items, list):
        raise AgendaError("the chapters must be a list")
    chapters: list[Chapter] = []
    for item in cast("list[object]", items):
        if not isinstance(item, dict):
            raise AgendaError("a chapter must be a JSON object")
        fields = cast("dict[str, object]", item)
        chapter_id, title = fields.get("id"), fields.get("title")
        if not isinstance(chapter_id, str) or _ID.fullmatch(chapter_id) is None:
            raise AgendaError(f"invalid chapter id: {chapter_id!r}")
        if not isinstance(title, str):
            raise AgendaError("a chapter title must be a string")
        chapters.append(Chapter(chapter_id, title))
    if len({c.id for c in chapters}) != len(chapters):
        raise AgendaError("chapter ids must be unique")
    return Agenda(tuple(chapters))
