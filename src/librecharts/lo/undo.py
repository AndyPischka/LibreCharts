# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Undo support for chart operations.

LibreOffice does not record shapes inserted through the API, so an undo context alone leaves a
no-op entry in the undo list. Instead, chart operations run with LibreOffice's own recording locked
and register one explicit action that knows how to undo and redo the whole change.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import unohelper
from com.sun.star.document import XUndoAction


class _Action(unohelper.Base, XUndoAction):
    def __init__(self, title: str, undo: Callable[[], None], redo: Callable[[], None]) -> None:
        self.Title = title  # UNO attribute XUndoAction::Title
        self._undo = undo
        self._redo = redo

    def undo(self) -> None:
        self._undo()

    def redo(self) -> None:
        self._redo()


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
    doc.getUndoManager().addUndoAction(_Action(title, undo, redo))
