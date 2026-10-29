# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The Calc window as a transient view on a chart's data (ADR 0003, M1 plan decision 2).

The chart state in the presentation is the source of truth. Opening the data sheet writes the
stored cells (values and formulas) into a new Calc document; every committed edit is read back
immediately, stored and redrawn. The Calc document is never saved: after each sync its modified
flag is reset, so closing the window does not ask to save it.

The data sheet of a linked chart (ADR 0020) is a protected, read-only view of the fetched values:
its source owns the data. An info bar offers to open the source or remove the link.
"""

from __future__ import annotations

import contextlib
import traceback
from dataclasses import replace
from typing import Any

import uno
import unohelper
from com.sun.star.document import XDocumentEventListener
from com.sun.star.lang import Locale
from com.sun.star.util import XModifyListener

from librecharts.core import links
from librecharts.core.datasheet import state_from_sheet
from librecharts.core.gantt import END, START
from librecharts.core.messages import text
from librecharts.core.model import ChartState
from librecharts.lo import chart, store

_DATE = 2  # com.sun.star.util.NumberFormat.DATE
_CONTENTS = 1 | 2 | 4 | 16  # com.sun.star.sheet.CellFlags VALUE, DATETIME, STRING, FORMULA
_INFO = 0  # com.sun.star.frame.InfobarType.INFO
_INFOBAR = "org.librecharts.linked"


class OrphanedChartError(Exception):
    """The chart's state is not stored in this document."""


# Open data sheets by (presentation RuntimeUID, chart id): one window per chart.
_sessions: dict[tuple[str, str], _Session] = {}


def open_datasheet(
    desktop: Any, doc: Any, group: Any, locale: str, load_args: tuple[Any, ...] = ()
) -> Any:
    """Open (or bring to front) the data sheet for the chart in ``group``; returns the Calc doc.

    Raises ``OrphanedChartError`` if the document has no state for the chart and ``StateError``
    if the stored state is unreadable.
    """
    chart_id = store.chart_id_of(group)
    if chart_id is None:
        raise ValueError("shape is not a LibreCharts chart")
    key = (str(doc.RuntimeUID), chart_id)
    if key in _sessions:
        _sessions[key].to_front()
        return _sessions[key].calc

    state = store.read_state(doc, chart_id)
    if state is None:
        raise OrphanedChartError(chart_id)
    calc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, load_args)
    _sessions[key] = _Session(key, doc, group, calc, state, locale)
    return calc


def refresh(doc: Any, chart_id: str) -> None:
    """Show the chart's stored state in its open data sheet, if it has one: after a link brought
    new data, or after the chart was linked or unlinked."""
    session = _sessions.get((str(doc.RuntimeUID), chart_id))
    if session is None:
        return
    state = store.read_state(doc, chart_id)
    if state is not None:
        session.show(state)


def owner(calc: Any) -> tuple[Any, Any] | None:
    """The presentation and the chart group whose data sheet ``calc`` is, else ``None``."""
    try:
        uid = str(calc.RuntimeUID)
    except Exception:  # not a document model
        return None
    for session in _sessions.values():
        if str(session.calc.RuntimeUID) == uid:
            return session.doc, session.group
    return None


class _Session:
    def __init__(
        self,
        key: tuple[str, str],
        doc: Any,
        group: Any,
        calc: Any,
        state: ChartState,
        locale: str,
    ) -> None:
        self.key, self.doc, self.group, self.calc, self.state = key, doc, group, calc, state
        self.locale = locale
        self._syncing = False
        self._show(state)
        self._doc_listener = _DocListener(self)
        self._calc_listener = _CalcListener(self)
        # Not doc.addEventListener: on documents that name is ambiguous in PyUNO (XComponent vs.
        # the legacy XEventBroadcaster) and picks the wrong one.
        doc.addDocumentEventListener(self._doc_listener)
        calc.addModifyListener(self._calc_listener)

    def sync(self) -> None:
        if self._syncing:  # setModified(False) below notifies the listener again
            return
        self._syncing = True
        try:
            chart_id = store.chart_id_of(self.group)
            stored = (store.read_state(self.doc, chart_id) if chart_id else None) or self.state
            if stored.link is not None:  # the source owns the data; the sheet is only a view
                self.calc.setModified(False)
                return
            read = self._read()
            # The data sheet owns cells and values only; annotations added meanwhile stay.
            state = replace(stored, cells=read.cells, values=read.values)
            if state != stored:
                chart.redraw(self.doc, self.group, state)
            self.state = state
            self.calc.setModified(False)
        except Exception:
            # Never let an exception escape into LibreOffice's notification loop.
            traceback.print_exc()
        finally:
            self._syncing = False

    def show(self, state: ChartState) -> None:
        """Write ``state`` into the open sheet, replacing what it showed."""
        self._syncing = True  # our own writes are no edits
        try:
            self._show(state)
            self.state = state
        except Exception:
            traceback.print_exc()
        finally:
            self._syncing = False

    def _show(self, state: ChartState) -> None:
        sheet = self._sheet()
        sheet.unprotect("")
        self._used().clearContents(_CONTENTS)
        if state.link is None:
            self._write(state)
        else:
            self._write_view(state)
        if state.kind == "gantt":
            self._show_dates()
        if state.link is not None:
            sheet.protect("")
        frame = self.calc.getCurrentController().getFrame()
        if state.link is None:
            frame.setTitle(text("datasheet_title", self.locale))
        else:
            source = links.describe(state.link)
            frame.setTitle(text("datasheet_title_linked", self.locale, source=source))
        self._info_bar(state)
        self.calc.setModified(False)

    def _info_bar(self, state: ChartState) -> None:
        """While linked: where the data comes from, with buttons to open the source or remove
        the link."""
        controller = self.calc.getCurrentController()
        with contextlib.suppress(Exception):  # hidden and headless windows have no info bar
            if controller.hasInfobar(_INFOBAR):
                controller.removeInfobar(_INFOBAR)
            if state.link is None or not controller.getFrame().getContainerWindow().isVisible():
                return
            buttons = tuple(
                uno.createUnoStruct(
                    "com.sun.star.beans.StringPair", text(key, self.locale), command
                )
                for key, command in (
                    ("menu_open_source", "org.librecharts:OpenSource"),
                    ("menu_remove_link", "org.librecharts:RemoveLink"),
                )
            )
            controller.appendInfobar(
                _INFOBAR,
                text("datasheet_linked", self.locale, source=links.describe(state.link)),
                text("datasheet_linked_hint", self.locale),
                _INFO,
                buttons,
                False,
            )

    def to_front(self) -> None:
        self.calc.getCurrentController().getFrame().getContainerWindow().toFront()

    def close(self) -> None:
        try:
            self.calc.close(True)
        except Exception:
            traceback.print_exc()

    def ended(self) -> None:
        _sessions.pop(self.key, None)
        with contextlib.suppress(Exception):  # the presentation may already be gone
            self.doc.removeDocumentEventListener(self._doc_listener)

    def _sheet(self) -> Any:
        return self.calc.getSheets().getByIndex(0)

    def _write(self, state: ChartState) -> None:
        if not state.cells or not state.cells[0]:
            return
        rows, columns = len(state.cells), len(state.cells[0])
        self._sheet().getCellRangeByPosition(0, 0, columns - 1, rows - 1).setFormulaArray(
            state.cells
        )

    def _write_view(self, state: ChartState) -> None:
        if not state.cells or not state.cells[0]:
            return
        rows, columns = len(state.cells), len(state.cells[0])
        self._sheet().getCellRangeByPosition(0, 0, columns - 1, rows - 1).setDataArray(
            links.view(state)
        )

    def _used(self) -> Any:
        sheet = self._sheet()
        cursor = sheet.createCursor()
        cursor.gotoEndOfUsedArea(False)
        end = cursor.getRangeAddress()
        return sheet.getCellRangeByPosition(0, 0, end.EndColumn, end.EndRow)

    def _show_dates(self) -> None:
        """Show the start and end columns of a Gantt sheet as dates, not serial numbers.

        The standard date format of the Calc document's locale, so that dates typed in that
        locale's style are recognised as well.
        """
        formats = self.calc.getNumberFormats()
        key = formats.getStandardFormat(_DATE, Locale())
        columns = self._sheet().getColumns()
        for column in (START, END):
            columns.getByIndex(column).NumberFormat = key

    def _read(self) -> ChartState:
        used = self._used()
        return state_from_sheet(
            self.state.kind, self.state.grouping, used.getFormulaArray(), used.getDataArray()
        )


class _CalcListener(unohelper.Base, XModifyListener):
    def __init__(self, session: _Session) -> None:
        self.session = session

    def modified(self, event: Any) -> None:
        self.session.sync()

    def disposing(self, event: Any) -> None:
        self.session.ended()


class _DocListener(unohelper.Base, XDocumentEventListener):
    """Closes the data sheet when the presentation goes away."""

    def __init__(self, session: _Session) -> None:
        self.session = session

    def documentEventOccured(self, event: Any) -> None:  # sic, UNO spelling
        if event.EventName == "OnUnload":
            self.session.close()

    def disposing(self, event: Any) -> None:
        self.session.close()
