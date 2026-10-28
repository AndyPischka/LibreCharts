# 0003. Edit chart data in a Calc window

- Status: accepted
- Date: 2026-10-28

## Context

Users of think-cell edit chart data in an Excel-like data sheet, with formulas and copy-paste.

## Decision

The data sheet is a Calc document window; values are synchronised back into the chart on the slide.

## Alternatives considered

- **Custom grid dialog**: full control and lean, but formulas, paste and fill handles would have to be
  built from scratch.

## Consequences

- Formulas, paste and number formats come for free.
- Synchronisation between Calc and the slide is the main technical risk; M1 starts with a spike
  and may result in a follow-up ADR.
