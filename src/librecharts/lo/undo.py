# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Undo support for chart operations.

LibreOffice does not record shapes inserted through the API, so an undo context alone leaves a
no-op entry in the undo list. Instead, chart operations run with LibreOffice's own recording locked
and register one explicit action that knows how to undo and redo the whole change.

The actions hold shapes (e.g. an inserted group, to put it back on redo). LibreOffice drops them
while it tears a closed document down, and PyUNO frees Python objects released by LibreOffice on a
thread of its own, after the drawing model is gone: a shape freed there takes its draw object and
the dead item pool with it, which crashed LibreOffice 25.8. So every action of a document lets go of
its callables when the document unloads, while the model is still alive.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import unohelper
from com.sun.star.document import XDocumentEventListener, XUndoAction

_actions: dict[str, list[_Action]] = {}


def _nothing() -> None:
    pass


class _Action(unohelper.Base, XUndoAction):
    def __init__(self, title: str, undo: Callable[[], None], redo: Callable[[], None]) -> None:
        self.Title = title  # UNO attribute XUndoAction::Title
        self._undo = undo
        self._redo = redo

    def undo(self) -> None:
        self._undo()

    def redo(self) -> None:
        self._redo()

    def release(self) -> None:
        """Drop the callables and with them every shape and document they hold."""
        self._undo = self._redo = _nothing


class _Unload(unohelper.Base, XDocumentEventListener):
    """Releases the actions of a document before LibreOffice tears its drawing model down."""

    def __init__(self, key: str) -> None:
        self.key = key

    def documentEventOccured(self, event: Any) -> None:  # sic, UNO spelling
        if event.EventName == "OnUnload":
            self._release()

    def disposing(self, event: Any) -> None:
        self._release()

    def _release(self) -> None:
        # Never let an exception escape into the notification of LibreOffice.
        try:
            for action in _actions.pop(self.key, []):
                action.release()
        except Exception:
            traceback.print_exc()


@contextmanager
def recording_locked(doc: Any) -> Iterator[None]:
    """Keep LibreOffice from recording its own (partial) undo actions inside the block."""
    manager = doc.getUndoManager()
    manager.lock()
    try:
        yield
    finally:
        manager.unlock()


def add_action(doc: Any, title: str, undo: Callable[[], None], redo: Callable[[], None]) -> None:
    action = _Action(title, undo, redo)
    key = str(doc.RuntimeUID)
    if key not in _actions:
        _actions[key] = []
        # Not doc.addEventListener: on documents that name is ambiguous in PyUNO (see datasheet).
        doc.addDocumentEventListener(_Unload(key))
    # Kept until the document unloads, also once LibreOffice dropped the action from its undo
    # list: only then is it sure that the last reference goes away while the model is alive.
    _actions[key].append(action)
    doc.getUndoManager().addUndoAction(action)
