# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Build a deck from a template and a deck specification (M18, ADR 0028).

A placeholder is a shape named ``librecharts-placeholder:<key>`` on any slide of the template. The
builder puts the chart the specification describes for that key at the placeholder's position and
size and removes the placeholder. Slides, master slides and the colour scheme of the template stay;
only placeholders and charts change.

Nothing is changed before every chart has its placeholder, so a broken specification leaves the
template as it was and writes no output file.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from typing import Any

import uno

from librecharts.core import deck as core_deck
from librecharts.core import links as core_links
from librecharts.core.deck import Deck, DeckError
from librecharts.lo import chart, links, ui

_NEVER_EXECUTE = 0  # com.sun.star.document.MacroExecMode.NEVER_EXECUTE
_NO_UPDATE = 0  # com.sun.star.document.UpdateDocMode.NO_UPDATE
_PRESENTATION = "com.sun.star.presentation.PresentationDocument"
_FILTERS = {"odp": "impress8", "pptx": "Impress MS PowerPoint 2007 XML"}


@dataclass(frozen=True, slots=True)
class Placeholder:
    """A placeholder shape of the template: its key, the slide it sits on and the shape itself."""

    key: str
    page: Any
    shape: Any


def placeholders(doc: Any) -> dict[str, list[Placeholder]]:
    """Every placeholder of ``doc`` by key, in slide order; a key may appear more than once.

    Only top-level shapes count: a placeholder inside a group is not found.
    """
    found: dict[str, list[Placeholder]] = {}
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for i in range(page.getCount()):
            shape = page.getByIndex(i)
            key = core_deck.placeholder_key(str(shape.Name))
            if key is not None:
                found.setdefault(key, []).append(Placeholder(key, page, shape))
    return found


def build(ctx: Any, template_url: str, spec: Deck, out_url: str, locale: str = "") -> str:
    """Replace the placeholders of the template with the charts of ``spec`` and save as ``out_url``.

    Returns what to tell the user: how many charts were written, and which placeholders stayed
    empty. Raises ``DeckError`` if the deck cannot be built; the template is then left untouched and
    no file is written.
    """
    template, target = links.as_url(template_url), links.as_url(out_url)
    document = _load(ctx, template)
    try:
        found = placeholders(document)
        missing = sorted(
            chart.placeholder for chart in spec.charts if chart.placeholder not in found
        )
        if missing:
            raise DeckError("deck_missing_placeholders", ", ".join(missing))
        duplicated = sorted(key for key, shapes in found.items() if len(shapes) > 1)
        if duplicated:
            raise DeckError("deck_duplicate_placeholders", ", ".join(duplicated))
        for entry in spec.charts:
            (placeholder,) = found[entry.placeholder]  # one only, checked above
            _replace(document, placeholder, entry.state)
        _save(document, target)
    finally:
        with contextlib.suppress(Exception):
            document.close(True)
    used = {chart.placeholder for chart in spec.charts}
    report = core_deck.built_report(len(spec.charts), core_links.file_name(target), locale)
    unused = core_deck.unused_report([key for key in found if key not in used], locale)
    return f"{report}\n{unused}" if unused else report


def read_spec(location: str) -> str:
    """The deck specification at ``location``: a file URL or a system path."""
    try:
        with open(uno.fileUrlToSystemPath(links.as_url(location)), encoding="utf-8") as file:
            return file.read()
    except OSError as exc:
        raise DeckError("deck_spec_unreadable", str(exc)) from exc


def _replace(doc: Any, placeholder: Placeholder, state: Any) -> None:
    """Put the chart of ``state`` where ``placeholder`` is and remove the placeholder."""
    position, size = placeholder.shape.Position, placeholder.shape.Size
    try:
        chart.insert_at(
            doc,
            placeholder.page,
            state,
            (position.X, position.Y, size.Width, size.Height),
            undo_action=False,
        )
    except ValueError as exc:  # the placeholder is smaller than the smallest layout
        raise DeckError("deck_placeholder_too_small", placeholder.key) from exc
    placeholder.page.remove(placeholder.shape)


def _load(ctx: Any, url: str) -> Any:
    """The template at ``url``, hidden and without running its macros."""
    name = core_links.file_name(url)
    args = (
        ui.prop("Hidden", True),
        ui.prop("MacroExecutionMode", _NEVER_EXECUTE),
        ui.prop("UpdateDocMode", _NO_UPDATE),
    )
    try:
        document = _desktop(ctx).loadComponentFromURL(url, "_blank", 0, args)
    except Exception as exc:  # not a document, password protected, ...
        raise DeckError("deck_open_failed", name) from exc
    if document is None or not document.supportsService(_PRESENTATION):
        if document is not None:
            with contextlib.suppress(Exception):
                document.close(True)
        raise DeckError("deck_open_failed", name)
    return document


def _save(document: Any, url: str) -> None:
    """Store ``document`` as ``url``; the file extension picks the filter (``.odp``, ``.pptx``)."""
    name = core_links.file_name(url)
    suffix = os.path.splitext(name)[1].lstrip(".").lower()
    filter_name = _FILTERS.get(suffix)
    if filter_name is None:
        raise DeckError("deck_save_failed", name)
    args = (ui.prop("FilterName", filter_name), ui.prop("Overwrite", True))
    try:
        document.storeToURL(url, args)
    except Exception as exc:  # e.g. the folder does not exist or is not writable
        raise DeckError("deck_save_failed", name) from exc


def _desktop(ctx: Any) -> Any:
    return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
