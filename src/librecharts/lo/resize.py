# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Re-lay out charts after the user resized them.

Each presentation gets one watcher (``watch``), registered by the document-open job in
extension/entry.py. Modify events are coalesced and handled asynchronously on the main thread, so
the document is never changed from inside its own notification. A chart is only looked at when its
group size differs from the last one seen; ``chart.fit_to_size`` then compares the shapes with the
layout for that size, which makes the check idempotent and safe across undo, redo and reloads.
"""

from __future__ import annotations

import traceback
from typing import Any

import uno
import unohelper
from com.sun.star.awt import XCallback
from com.sun.star.util import XModifyListener

from librecharts.lo import chart, store

_watchers: dict[str, _Watcher] = {}


def watch(doc: Any) -> None:
    """Start watching ``doc`` for resized charts (idempotent)."""
    key = str(doc.RuntimeUID)
    if key not in _watchers:
        _watchers[key] = _Watcher(key, doc)


def is_watched(doc: Any) -> bool:
    return str(doc.RuntimeUID) in _watchers


class _Watcher(unohelper.Base, XModifyListener, XCallback):
    def __init__(self, key: str, doc: Any) -> None:
        self.key, self.doc = key, doc
        self._sizes: dict[str, tuple[int, int]] = {}
        self._pending = False
        self._busy = False
        ctx = uno.getComponentContext()
        self._async = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx
        )
        for group, _ in store.all_charts(doc):
            self._sizes[group.Name] = (group.Size.Width, group.Size.Height)
        doc.addModifyListener(self)

    # XModifyListener
    def modified(self, event: Any) -> None:
        if self._pending or self._busy:  # coalesce, and ignore our own changes
            return
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

    # XCallback
    def notify(self, data: Any) -> None:
        self._pending = False
        self._busy = True
        try:
            for group, _ in store.all_charts(self.doc):
                size = (group.Size.Width, group.Size.Height)
                if self._sizes.get(group.Name) == size:
                    continue
                chart.fit_to_size(self.doc, group)
                self._sizes[group.Name] = (group.Size.Width, group.Size.Height)
        except Exception:
            # Never let an exception escape into the event handling of LibreOffice.
            traceback.print_exc()
        finally:
            self._busy = False
