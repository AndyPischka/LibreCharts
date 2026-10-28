# 0005. The Calc data sheet is a transient view, synchronised on every edit

- Status: accepted (refines [0003](0003-calc-datasheet.md))
- Date: 2026-10-28

## Context

ADR 0003 chose a Calc window for editing chart data. Open questions were what is authoritative, when
to sync, and what happens to formulas and to the window's lifetime.

## Decision

- The chart state in the presentation (ADR 0004) is the source of truth. The Calc document is a view.
- *Edit chart data* opens a new Calc document and writes the stored raw cells, formulas included.
  One window per chart; opening again focuses it.
- A modify listener reads the used range after every committed edit (formulas via `getFormulaArray`,
  results via `getDataArray`; Calc evaluates, `core` never does), stores the state and redraws the
  chart. No debounce: Calc reports committed edits, not keystrokes.
- After each sync the Calc document's modified flag is reset, so closing it never asks to save. It is
  never written to disk.
- Closing the presentation closes its data sheets (`addDocumentEventListener`).
- The data sheet opens hidden when the presentation is hidden (macros, tests).
- Layout (rows = series, columns = categories) and parsing live in `core/datasheet.py`.

## Alternatives considered

- **Custom grid dialog**: see ADR 0003.
- **Debounced sync**: more code, and no benefit because edits arrive committed.
- **Calc document as source of truth** (saved or embedded): ties the chart to a second file or an OLE object.

## Consequences

- Formulas survive closing and reopening, but only references inside the sheet make sense.
- Every edit is one undo step in the presentation (explicit undo actions, `lo/undo.py`).
- Pitfalls found on the way: `addEventListener` is ambiguous on documents in PyUNO; an exception escaping
  a dispatch or listener can abort LibreOffice; LibreOffice 26.8 intermittently aborts in headless mode
  when a visible Calc window is closed (hence hidden test documents).
- Double-click opens the data sheet too (added later, `lo/doubleclick.py`): a mouse click handler
  swallows the second press on a selected chart, which Impress would use to enter the group.
