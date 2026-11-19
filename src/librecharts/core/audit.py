"""Auditing a presentation: charts, links, stale sources and design deviations (M29)."""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.messages import text


@dataclass(frozen=True, slots=True)
class Finding:
    slide: int  # 1-based
    key: str
    detail: str = ""


def report(findings: tuple[Finding, ...], locale: str = "en") -> str:
    """A plain report, one finding per line; an empty presentation is reported as clean."""
    if not findings:
        return text("audit_clean", locale)
    lines = [text("audit_summary", locale, count=str(len(findings)))]
    lines += [
        text(
            "audit_line",
            locale,
            slide=str(finding.slide),
            message=text(finding.key, locale, detail=finding.detail),
        )
        for finding in findings
    ]
    return "\n".join(lines)
