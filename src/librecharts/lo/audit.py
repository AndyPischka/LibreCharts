# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Walk a presentation and collect audit findings (M29)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import uno

from librecharts.core.audit import Finding
from librecharts.core.state_io import StateError
from librecharts.lo import store


def inspect(doc: Any) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    pages = doc.getDrawPages()
    for index in range(pages.getCount()):
        page = pages.getByIndex(index)
        for group, chart_id in store.find_charts(page):
            try:
                state = store.read_state(doc, chart_id)
            except StateError as exc:
                findings.append(Finding(index + 1, "audit_corrupt_chart", str(exc)))
                continue
            if state is None:
                findings.append(Finding(index + 1, "audit_corrupt_chart", str(group.Name)))
                continue
            if state.link is not None:
                findings.append(Finding(index + 1, "audit_linked"))
                if _stale(state.link.url, state.link.modified):
                    findings.append(Finding(index + 1, "audit_stale_link", state.link.url))
    return tuple(findings)


def _stale(url: str, modified: str) -> bool:
    try:
        path = Path(uno.fileUrlToSystemPath(url))
        if not modified:
            return False
        return str(path.stat().st_mtime) != modified
    except Exception:
        return False
