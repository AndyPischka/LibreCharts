# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Re-lay out charts after the user resized them, and keep labels the user moved (ADR 0023).

Each presentation gets one watcher (``watch``), registered by the document-open job in
extension/entry.py. Modify events are coalesced and handled asynchronously on the main thread, so
the document is never changed from inside its own notification. A chart is only looked at when the
size of its layout box (the invisible frame, ``render.layout_box``) differs from the last one seen;
``chart.fit_to_size`` then compares the shapes with the layout for that size, which makes the check
idempotent and safe across undo, redo and reloads.

Reading every child of a chart costs milliseconds, so the children are only read where a label can
have moved (``lo/labels.py``): in the chart whose child is selected (a label is selected while it
is dragged, nudged or placed with the position dialog, and after an undo or redo inside the group),
and in the charts of the current slide after an undo or redo that is not one of ours.

The watcher never outlives its document: when the document disposes it, the watcher unregisters
its listeners and drops its reference to the document on the document's own thread, so no proxy
of it stays behind for pyuno's garbage collector to release later on its background thread (the
mechanism behind the LibreOffice teardown crashes of issue #4).
"""

from __future__ import annotations

import contextlib
import traceback
from typing import Any

import uno
import unohelper
from com.sun.star.awt import XCallback
from com.sun.star.document import XUndoManagerListener
from com.sun.star.util import XModifyListener

from librecharts.lo import chart, labels, render, samescale, store
from librecharts.lo import elements as slide_elements

_watchers: dict[str, _Watcher] = {}
_OURS = "LibreCharts"  # in the title of every undo action of ours


def watch(doc: Any) -> None:
    """Start watching ``doc`` for resized charts and moved labels (idempotent)."""
    key = str(doc.RuntimeUID)
    if key not in _watchers:
        _watchers[key] = _Watcher(key, doc)


def is_watched(doc: Any) -> bool:
    return str(doc.RuntimeUID) in _watchers


class _Watcher(unohelper.Base, XModifyListener, XUndoManagerListener, XCallback):
    def __init__(self, key: str, doc: Any) -> None:
        self.key = key
        self.doc: Any = doc
        self._sizes: dict[str, tuple[int, int]] = {}
        self._pending = False
        self._busy = False
        self._undone = False  # an undo or redo that is not ours happened since the last look
        ctx = uno.getComponentContext()
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        for group, _ in store.all_charts(doc):
            self._sizes[group.Name] = render.layout_box(group)[2:]
        doc.addModifyListener(self)
        doc.getUndoManager().addUndoManagerListener(self)

    # XModifyListener
    def modified(self, event: Any) -> None:
        if self._pending or self._busy:  # coalesce, and ignore our own changes
            return
        self._schedule()

    def _schedule(self) -> None:
        try:
            # None is the void "any". An explicit uno.Any("void", None) works on LibreOffice 26.8
            # but is rejected by the PyUNO of 25.8 ("uno.Any instance not accepted").
            self._async.addCallback(self, None)
            self._pending = True
        except Exception:
            # Never let an exception escape into the notification of LibreOffice.
            traceback.print_exc()

    def disposing(self, event: Any) -> None:
        _watchers.pop(self.key, None)
        # Unregister on the document's own dispose thread and drop the document reference, so
        # that no stale proxy of the document or its shapes stays behind in this Python object;
        # pyuno's garbage collector thread would otherwise release it later from a bridge thread
        # while LibreOffice is already tearing the document down (issue #4).
        with contextlib.suppress(Exception):  # the document is already going away
            self.doc.removeModifyListener(self)
        with contextlib.suppress(Exception):
            self.doc.getUndoManager().removeUndoManagerListener(self)
        self.doc = None
        self._sizes.clear()

    # XUndoManagerListener
    def actionUndone(self, event: Any) -> None:
        self._undone_or_redone(event)

    def actionRedone(self, event: Any) -> None:
        self._undone_or_redone(event)

    def _undone_or_redone(self, event: Any) -> None:
        try:
            if _OURS not in str(event.UndoActionTitle):
                self._undone = True
                if not (self._pending or self._busy):
                    self._schedule()
        except Exception:
            traceback.print_exc()

    def undoActionAdded(self, event: Any) -> None:
        pass

    def allActionsCleared(self, event: Any) -> None:
        pass

    def redoActionsCleared(self, event: Any) -> None:
        pass

    def resetAll(self, event: Any) -> None:
        pass

    def enteredContext(self, event: Any) -> None:
        pass

    def enteredHiddenContext(self, event: Any) -> None:
        pass

    def leftContext(self, event: Any) -> None:
        pass

    def leftHiddenContext(self, event: Any) -> None:
        pass

    def cancelledContext(self, event: Any) -> None:
        pass

    # XCallback
    def notify(self, data: Any) -> None:
        self._pending = False
        if self.doc is None:  # the document is gone; the watcher waits to be collected
            return
        if samescale.is_busy(self.doc):  # our own redraw: nothing to find in half-updated shapes
            return
        self._busy = True
        try:
            inspect = self._charts_to_inspect()
            for group, _ in store.all_charts(self.doc):
                size = render.layout_box(group)[2:]
                if self._sizes.get(group.Name) != size:
                    chart.fit_to_size(self.doc, group)
                    self._sizes[group.Name] = render.layout_box(group)[2:]
                elif group.Name in inspect:
                    labels.check(self.doc, group)
            # Elements share their names, so their sizes are not tracked; the check is idempotent.
            for group, _ in slide_elements.all_elements(self.doc):
                slide_elements.fit_to_size(group)
        except Exception:
            # Never let an exception escape into the event handling of LibreOffice.
            traceback.print_exc()
        finally:
            self._busy = False

    def _charts_to_inspect(self) -> set[str]:
        """The names of the charts a label may have moved in (see the module docstring)."""
        names: set[str] = set()
        controller = self.doc.getCurrentController()
        if controller is None:
            return names
        if self._undone:
            self._undone = False
            page = controller.getCurrentPage()
            if page is not None:
                names.update(str(group.Name) for group, _ in store.find_charts(page))
        selection = controller.getSelection()
        if selection is None or _is_chart(selection):  # the whole chart, not a child of it
            return names
        count = selection.getCount() if hasattr(selection, "getCount") else 0
        for index in range(count):
            try:
                parent = selection.getByIndex(index).getParent()
                if store.chart_id_of(parent) is not None:
                    names.add(str(parent.Name))
            except AttributeError:  # not a shape inside a group
                continue
        return names


def _is_chart(shape: Any) -> bool:
    try:
        return store.chart_id_of(shape) is not None
    except AttributeError:  # e.g. a shape collection has no Name
        return False
