# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The Calc window as a transient view on a chart's data (ADR 0003, M1 plan decision 2).

The chart state in the presentation is the source of truth. Opening the data sheet writes the
stored cells (values and formulas) into a new Calc document; every committed edit is read back
immediately, stored and redrawn. The Calc document is never saved: after each sync its modified
flag is reset, so closing the window does not ask to save it.
"""

from __future__ import annotations

import contextlib
import traceback
from dataclasses import replace
from typing import Any

import unohelper
from com.sun.star.document import XDocumentEventListener
from com.sun.star.util import XModifyListener

from librecharts.core.datasheet import state_from_sheet
from librecharts.core.model import ChartState
from librecharts.lo import chart, store


class OrphanedChartError(Exception):
    """The chart's state is not stored in this document."""


# Open data sheets by (presentation RuntimeUID, chart id): one window per chart.
_sessions: dict[tuple[str, str], _Session] = {}


def open_datasheet(
    desktop: Any, doc: Any, group: Any, title: str, load_args: tuple[Any, ...] = ()
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
    _sessions[key] = _Session(key, doc, group, calc, state, title)
    return calc


class _Session:
    def __init__(
        self, key: tuple[str, str], doc: Any, group: Any, calc: Any, state: ChartState, title: str
    ) -> None:
        self.key, self.doc, self.group, self.calc, self.state = key, doc, group, calc, state
        self._syncing = False
        self._write(state)
        calc.setModified(False)
        calc.getCurrentController().getFrame().setTitle(title)
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

    def _read(self) -> ChartState:
        sheet = self._sheet()
        cursor = sheet.createCursor()
        cursor.gotoEndOfUsedArea(False)
        end = cursor.getRangeAddress()
        used = sheet.getCellRangeByPosition(0, 0, end.EndColumn, end.EndRow)
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
