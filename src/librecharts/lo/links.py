# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Data links in a presentation: read the linked ranges of external spreadsheets (ADR 0020).

A source is opened hidden, read-only and with macros never executed, read and closed again. A
source the user has open already is read as it is, unsaved edits included, and left open. Every
source is opened once per update, however many charts it feeds. Rules about ranges, URLs and the
fetched grid live in ``core/links.py``; the commands in ``lo/commands.py`` store the results.
"""

from __future__ import annotations

import contextlib
import datetime
import os
import re
import threading
import traceback
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any

import uno
import unohelper
from com.sun.star.awt import XCallback

from librecharts.core import links
from librecharts.core.links import Problem
from librecharts.core.messages import text
from librecharts.core.model import ChartState, Link
from librecharts.core.state_io import StateError
from librecharts.lo import store, ui

_NEVER_EXECUTE = 0  # com.sun.star.document.MacroExecMode.NEVER_EXECUTE
_NO_UPDATE = 0  # com.sun.star.document.UpdateDocMode.NO_UPDATE: keep the source's own links
_SPREADSHEET = "com.sun.star.sheet.SpreadsheetDocument"
_INFO = 0  # com.sun.star.frame.InfobarType.INFO
_OFFER_ATTEMPTS, _OFFER_RETRY_S = 20, 0.25
INFOBAR = "org.librecharts.links"
UPDATE_ALL = "org.librecharts:UpdateAllLinks"


class LinkError(Exception):
    """A link cannot be read; ``key`` is the message key of the reason."""

    def __init__(self, key: str, link: Link | None = None) -> None:
        super().__init__(key)
        self.key, self.link = key, link

    def message(self, locale: str) -> str:
        if self.link is None:
            return text(self.key, locale)
        return links.reason(self.key, self.link, locale)


@dataclass(slots=True)
class Target:
    """A linked chart to update; ``slide`` counts from 1, for messages."""

    group: Any
    chart_id: str
    state: ChartState
    link: Link
    slide: int


@dataclass(slots=True)
class Outcome:
    """What an update found, by chart id: new data, the same data (only the link's times are
    new), and the charts that could not be read."""

    changed: dict[str, tuple[Any, ChartState]] = field(default_factory=dict)
    unchanged: dict[str, ChartState] = field(default_factory=dict)
    problems: list[Problem] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Workbook:
    """What the link dialog offers from a source: its sheets with their used areas, and the
    names of its named ranges."""

    sheets: tuple[str, ...]
    used: tuple[str, ...]
    names: tuple[str, ...]


def targets(doc: Any, ids: set[str] | None = None, *, claim: bool = True) -> list[Target]:
    """Every linked chart of ``doc``, or those with an id in ``ids``, in slide order.

    Renamed copies are claimed first (``store.claim``), since an update edits them; with
    ``claim=False`` they stand for their origin and nothing in ``doc`` changes.
    """
    found: list[Target] = []
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        for group, _ in store.find_charts(pages.getByIndex(index)):
            chart_id = store.claim(doc, group) if claim else store.resolve(doc, group)
            if chart_id is None or (ids is not None and chart_id not in ids):
                continue
            try:
                state = store.read_state(doc, chart_id)
            except StateError:
                continue
            if state is not None and state.link is not None:
                found.append(Target(group, chart_id, state, state.link, index + 1))
    return found


def update(ctx: Any, doc: Any, charts: list[Target]) -> Outcome:
    """Read the sources of ``charts``; nothing is stored or drawn here."""
    outcome = Outcome()
    sources: dict[str, list[Target]] = {}
    for target in charts:
        try:
            url = locate(ctx, doc, target.link)
        except LinkError as exc:
            outcome.problems.append(Problem(target.slide, target.link, exc.key))
            continue
        same = next((known for known in sources if links.same_file(known, url)), url)
        sources.setdefault(same, []).append(target)
    now = datetime.datetime.now().isoformat(timespec="minutes")
    presentation = str(doc.getURL())
    for url, group in sources.items():
        try:
            with opened(ctx, url) as source:
                modified = modification_time(ctx, url)
                for target in group:
                    try:
                        results, shown = read(source, target.link)
                    except LinkError as exc:
                        outcome.problems.append(Problem(target.slide, target.link, exc.key))
                        continue
                    fresh = replace(
                        target.link,
                        url=url,
                        relative=links.relative_url(url, presentation),
                        updated=now,
                        modified=modified,
                    )
                    state = links.fetched(target.state, fresh, results, shown)
                    if links.same_data(state, target.state):
                        outcome.unchanged[target.chart_id] = state
                    else:
                        outcome.changed[target.chart_id] = (target.group, state)
        except LinkError as exc:
            outcome.problems += [Problem(t.slide, t.link, exc.key) for t in group]
    return outcome


def link(ctx: Any, doc: Any, state: ChartState, url: str, sheet: str, reference: str) -> ChartState:
    """``state`` linked to ``reference`` on ``sheet`` (``""``: a named range) of the source at
    ``url``, with the source's data. Raises ``LinkError``."""
    if not url.strip():
        raise LinkError("link_no_file")
    draft = Link(url=url, sheet=sheet, range=reference)
    outcome = update(ctx, doc, [Target(None, "", replace(state, link=draft), draft, 0)])
    if outcome.problems:
        raise LinkError(outcome.problems[0].key, draft)
    return next(iter([*(new for _, new in outcome.changed.values()), *outcome.unchanged.values()]))


def locate(ctx: Any, doc: Any, link: Link) -> str:
    """The URL the source is found at: next to the presentation if both moved, else where it
    was. Raises ``LinkError`` if it is nowhere."""
    access = _file_access(ctx)
    for url in links.candidates(link, str(doc.getURL())):
        if open_document(ctx, url) is not None:
            return url
        with contextlib.suppress(Exception):  # an unusable URL counts as missing
            if access.exists(url):
                return url
    raise LinkError("link_missing", link)


def open_document(ctx: Any, url: str) -> Any:
    """The spreadsheet at ``url`` if it is open in this LibreOffice, else ``None``."""
    components = _desktop(ctx).getComponents().createEnumeration()
    while components.hasMoreElements():
        component = components.nextElement()
        if not hasattr(component, "getURL"):  # not a document model (e.g. the Basic IDE)
            continue
        location = str(component.getURL())
        if location and links.same_file(location, url) and component.supportsService(_SPREADSHEET):
            return component
    return None


@contextlib.contextmanager
def opened(ctx: Any, url: str) -> Iterator[Any]:
    """The source at ``url``: the open document, or a hidden read-only copy closed afterwards."""
    source = open_document(ctx, url)
    if source is not None:
        yield source
        return
    source = _load(ctx, url)
    try:
        yield source
    finally:
        with contextlib.suppress(Exception):
            source.close(True)


def _load(ctx: Any, url: str) -> Any:
    args = [
        ui.prop("Hidden", True),
        ui.prop("ReadOnly", True),
        ui.prop("MacroExecutionMode", _NEVER_EXECUTE),
        ui.prop("UpdateDocMode", _NO_UPDATE),
    ]
    if url.lower().endswith(".csv"):
        args += [
            ui.prop("FilterName", links.CSV_FILTER),
            ui.prop("FilterOptions", links.csv_options(_first_line(url))),
        ]
    try:
        source = _desktop(ctx).loadComponentFromURL(url, "_blank", 0, tuple(args))
    except Exception as exc:  # e.g. password protected, or not a document at all
        raise LinkError("link_open_failed") from exc
    if source is None:
        raise LinkError("link_open_failed")
    if not source.supportsService(_SPREADSHEET):
        with contextlib.suppress(Exception):
            source.close(True)
        raise LinkError("link_open_failed")
    return source


def _first_line(url: str) -> str:
    try:
        with open(uno.fileUrlToSystemPath(url), encoding="utf-8", errors="replace") as file:
            return file.readline()
    except Exception:  # not a local file: let Calc's defaults decide
        return ""


def read(source: Any, link: Link) -> tuple[Any, tuple[tuple[str, ...], ...]]:
    """The linked range of ``source``: ``getDataArray`` and the displayed text of every cell."""
    cells = _cell_range(source, link)
    area = cells.getRangeAddress()
    rows = area.EndRow - area.StartRow + 1
    columns = area.EndColumn - area.StartColumn + 1
    problem = links.check_size(rows, columns)
    if problem is not None:
        raise LinkError(problem)
    shown = tuple(
        tuple(cells.getCellByPosition(c, r).getString() for c in range(columns))
        for r in range(rows)
    )
    return cells.getDataArray(), shown


def _cell_range(source: Any, link: Link) -> Any:
    if link.sheet:
        sheets = source.getSheets()
        if not sheets.hasByName(link.sheet):
            raise LinkError("link_no_sheet")
        try:
            return sheets.getByName(link.sheet).getCellRangeByName(link.range)
        except Exception as exc:
            raise LinkError("link_no_range") from exc
    names = source.NamedRanges
    if not names.hasByName(link.range):
        raise LinkError("link_no_range")
    cells = names.getByName(link.range).getReferredCells()
    if cells is None:  # a name for a formula or constant, not for cells
        raise LinkError("link_no_range")
    return cells


def inspect(ctx: Any, url: str) -> Workbook:
    """The sheets, used areas and range names of the source at ``url``, for the link dialog."""
    with opened(ctx, url) as source:
        sheets = source.getSheets()
        names = tuple(str(name) for name in sheets.getElementNames())
        used = tuple(_used_area(sheets.getByName(name)) for name in names)
        ranges = tuple(str(name) for name in source.NamedRanges.getElementNames())
    return Workbook(names, used, ranges)


def _used_area(sheet: Any) -> str:
    cursor = sheet.createCursor()
    cursor.gotoStartOfUsedArea(False)
    cursor.gotoEndOfUsedArea(True)
    area = cursor.getRangeAddress()
    return links.address(area.StartColumn, area.StartRow, area.EndColumn, area.EndRow)


def modification_time(ctx: Any, url: str) -> str:
    """When the file at ``url`` was last saved, as an ISO text; empty if that cannot be read.

    Only ever compared for equality with an earlier reading, so its time zone does not matter.
    """
    try:
        stamp = _file_access(ctx).getDateTimeModified(url)
    except Exception:
        return ""
    return (
        f"{stamp.Year:04}-{stamp.Month:02}-{stamp.Day:02}T"
        f"{stamp.Hours:02}:{stamp.Minutes:02}:{stamp.Seconds:02}.{stamp.NanoSeconds:09}"
    )


def show_source(ctx: Any, doc: Any, link: Link, hidden: bool) -> Any:
    """Open the source for the user (or bring it to the front) and select the linked range."""
    url = locate(ctx, doc, link)
    source = open_document(ctx, url)
    if source is None:
        args = (ui.prop("Hidden", True),) if hidden else ()
        try:
            source = _desktop(ctx).loadComponentFromURL(url, "_default", 0, args)
        except Exception as exc:
            raise LinkError("link_open_failed", link) from exc
        if source is None:
            raise LinkError("link_open_failed", link)
    else:
        with contextlib.suppress(Exception):
            source.getCurrentController().getFrame().getContainerWindow().toFront()
    with contextlib.suppress(Exception):  # the range may be gone; the file is open anyway
        source.getCurrentController().select(_cell_range(source, link))
    return source


def changed_sources(ctx: Any, doc: Any) -> list[str]:
    """Ids of the linked charts whose source was saved since their last update.

    Compares modification times only; nothing is opened. Missing sources are left to the update
    to report.
    """
    changed: list[str] = []
    for target in targets(doc, claim=False):  # runs when a deck opens: change nothing
        try:
            url = locate(ctx, doc, target.link)
        except LinkError:
            continue
        if modification_time(ctx, url) != target.link.modified:
            changed.append(target.chart_id)
    return changed


# Pending offers by presentation: a Python object passed to AsyncCallback must stay alive.
_offers: dict[str, _Offer] = {}


def offer_update(ctx: Any, doc: Any) -> None:
    """Show an info bar above ``doc`` if linked data changed, with an "Update now" button.

    Called by the document-open job, which runs before the document's view is complete: until
    then ``appendInfobar`` raises "Could not create Infobar". So the bar is added asynchronously
    and tried again for a few seconds until it shows. Never updates by itself: opening a
    presentation must not modify it (ADR 0020).
    """
    key = str(doc.RuntimeUID)
    if key not in _offers:
        _offers[key] = _Offer(key, ctx, doc)


class _Offer(unohelper.Base, XCallback):
    def __init__(self, key: str, ctx: Any, doc: Any) -> None:
        self.key, self.ctx, self.doc = key, ctx, doc
        self.attempts = 0
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        self._post()

    def _post(self) -> None:
        self._async.addCallback(self, None)  # None: void any, see lo/resize.py

    def notify(self, data: Any) -> None:
        self.attempts += 1
        try:
            shown = _offer(self.ctx, self.doc)
        except Exception:  # no info bar container yet, or the document closed meanwhile
            shown = False
        try:
            if shown or self.attempts >= _OFFER_ATTEMPTS:
                _offers.pop(self.key, None)
            else:
                threading.Timer(_OFFER_RETRY_S, self._post).start()
        except Exception:
            # Never let an exception escape into LibreOffice's callback processing.
            traceback.print_exc()
            _offers.pop(self.key, None)


def _offer(ctx: Any, doc: Any) -> bool:
    """Add the info bar if linked data changed; whether everything that should show does."""
    if not changed_sources(ctx, doc):
        return True
    locale = ui.ui_locale(ctx)
    controller = doc.getCurrentController()
    if controller.hasInfobar(INFOBAR):
        return True
    button = uno.createUnoStruct(
        "com.sun.star.beans.StringPair", text("infobar_update_now", locale), UPDATE_ALL
    )
    controller.appendInfobar(
        INFOBAR,
        text("infobar_links_changed", locale),
        text("infobar_links_question", locale),
        _INFO,
        (button,),
        True,
    )
    return bool(controller.hasInfobar(INFOBAR))


def withdraw_offer(doc: Any) -> None:
    """Remove the info bar of :func:`offer_update`, if it is shown."""
    with contextlib.suppress(Exception):  # no info bar in hidden or headless windows
        controller = doc.getCurrentController()
        if controller.hasInfobar(INFOBAR):
            controller.removeInfobar(INFOBAR)


def as_url(location: str) -> str:
    """A URL for ``location``, which may also be a system path (scripts and tests)."""
    location = location.strip()
    if not location or (re.match(r"[A-Za-z][A-Za-z0-9+.-]+:", location) and "://" in location):
        return location
    return str(uno.systemPathToFileUrl(os.path.abspath(location)))


def _desktop(ctx: Any) -> Any:
    return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)


def _file_access(ctx: Any) -> Any:
    return ctx.ServiceManager.createInstanceWithContext("com.sun.star.ucb.SimpleFileAccess", ctx)
