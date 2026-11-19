# 0039. Deck audit and specification export

- Status: accepted
- Date: 2026-11-20

## Context

A deck with many charts needs a quick check for unreadable states, links and stale sources, and a
way to take an existing deck back into automation.

## Decision

- **`core/audit.py`** turns findings into a plain report; `lo/audit.py` walks slides and reads chart
  states, links and source modification times. A finding names its 1-based slide.
- **`core/deck_export.py`** writes one chart entry per chart, using the same fields the deck
  specification accepts. Tables and matrices are skipped (their specs are not part of the deck
  format yet).
- The commands are `AuditDeck` and `ExportDeckSpec`; both are available from the sidebar's
  Document section.

## Consequences

The audit is read-only. Jump-to-slide, batch operations and design deviations in the audit are
follow-ups; the corporate design check remains a separate command (ADR 0029).
