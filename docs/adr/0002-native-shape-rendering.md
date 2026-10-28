# 0002. Render charts as native Draw shapes

- Status: accepted
- Date: 2026-10-28

## Context

think-cell-style charts need full control over layout: waterfall connectors, Marimekko widths,
difference and CAGR arrows, total labels above columns.

## Decision

A chart is a group of native Draw shapes (rectangles, lines, text) created by the `lo/` adapter from
geometry computed in `core/`.

## Alternatives considered

- **LibreOffice chart2 objects**: less code, but waterfall, Marimekko and arrow annotations are
  practically unachievable.
- **Hybrid** (chart2 for standard types, shapes for special ones): two code paths for little gain.

## Consequences

- We own the layout code (which lives in the testable `core/`).
- The slide renders correctly without the extension installed.
- Editing needs the chart's data stored alongside the shapes. Where and how is open
  (see "Not yet decided" in [ARCHITECTURE.md](../../ARCHITECTURE.md)).
