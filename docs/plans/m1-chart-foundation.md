# Plan: M1 chart foundation (persistence, data sheet, column charts)

Status: **agreed 2026-10-28** (answers in "Decisions by the maintainer"). Delete after M1; decisions move to ADRs 0004-0006.

## Goal

A user inserts a stacked or clustered column chart, edits its values in a Calc window, the slide
updates, and after saving (ODP or PPTX), reopening and double-clicking the chart, editing continues.
Everything M2-M4 need (state model, layout pipeline, rendering, sync) is built here once.

## Measured facts (spike, LibreOffice 26.8, Windows, 2026-10-28)

A group of two rectangles was saved as ODP and PPTX and reloaded. Payload: 1.2 KB JSON.

| Storage location | ODP | PPTX | Travels with copy/paste | Notes |
|---|---|---|---|---|
| `GroupShape.UserDefinedAttributes` | - | - | - | Group has no such property |
| `UserDefinedAttributes` of a child shape | yes | **lost** | yes (presumably) | |
| Group `Title` / `Description` (alt text) | yes | **lost** | yes | Also misuses accessibility fields |
| Hidden child text shape carrying JSON | yes | content kept, **becomes visible** | yes | Unacceptable: JSON blob on slide |
| Group `Name` | yes | yes | yes | Short id only |
| Document custom property (`UserDefinedProperties`) | yes | yes, also at 95 KB | **no** | Lives in the document, not the shape |
| Calc `XModifyListener` | fires on value and formula edits; formulas evaluate | | | |

Not measured yet: clipboard behaviour (needs a visible frame), undo grouping, resize detection.

## Decision 1: where chart state lives (-> ADR 0004)

**Recommendation:** the group's `Name` is an anchor `librecharts:<chart-id>`; the full state is JSON in a
document custom property `librecharts:<chart-id>`. This is the only combination that survives ODP and
PPTX, the format consultants exchange.

Consequences and how to handle them:
- **Duplicate within a document** (copy slide, Ctrl+C/V): two groups share one id. When a chart is
  opened for editing and its id is not unique, fork: give this group a new id and copy the state.
- **Copy into another document:** the state stays behind. The chart still looks correct (native
  shapes, ADR 0002) but is *orphaned*. M1: show "chart data not found in this document" and offer
  nothing more. Later option: also keep a redundant copy in a child shape's `UserDefinedAttributes`,
  which travels with ODP copy/paste, and restore from it when the document property is missing.
- **Garbage:** properties whose chart id no longer exists on any slide are removed on save
  (`XDocumentEventListener`, `OnSave`) or by an explicit "clean up" command. Never delete on load.
- The state carries a `"v"` schema version; `core` owns migrations.

Rejected: child-shape attributes or alt text as primary (lost in PPTX); hidden carrier shape
(visible after PPTX); an embedded Calc OLE object per chart (heavy, odd in PowerPoint, and we would
still need our own settings storage).

## Decision 2: data sheet sync (-> ADR 0005, refines ADR 0003)

The Calc document is a **transient view**, not the source of truth.

1. Double-click / "Edit data": create a new Calc document (visible window, title
   "LibreCharts data - <chart name>"), write the stored sheet cells (values *and* formulas) back.
2. `XModifyListener` on the Calc document: debounce (about 300 ms), read the used range, parse it
   with `core` (tolerating empty cells and text), update the state, re-layout, re-render the group.
3. Closing the Calc window: final sync, then dispose; the Calc document is never saved to disk.
4. Re-rendering replaces the group's children in place, so position, size and z-order of the group
   are preserved, and wraps all changes in one undo action (`XUndoManager.enterUndoContext`).
5. One open data sheet per chart; opening again focuses the existing window.

**Formulas are persisted.** The state keeps the sheet as a grid of raw cell contents read with
`XCell.getFormula()` (English function names, A1 references; plain numbers and text as they are)
next to the evaluated values the chart is drawn from. Only references inside the data sheet are
supported; references to other sheets or files are kept as text but marked as unsupported in the UI.
Evaluated values are taken from Calc, never re-computed in `core`.

Open: what happens to the Calc window when the presentation is closed first (proposal: final sync, then close it).

## Decision 3: module layout (-> ARCHITECTURE.md, ADR 0006 for the state schema)

```
core/model.py      ChartState (frozen dataclasses): version, kind, sheet (raw cells), values, style
core/state_io.py   to_json / from_json with schema version and migrations; strict validation
core/datasheet.py  table <-> ChartState (rows = series, columns = categories, like think-cell)
core/layout/column.py  ChartState + width/height -> list of primitives
core/primitives.py Rect, Line, Text (pure geometry in 1/100 mm, style references)
lo/render.py       primitives -> Draw shapes in a group; replaces children in place
lo/store.py        read/write document properties, chart id anchor, fork/orphan detection
lo/datasheet.py    Calc window lifecycle and modify listener
extension/entry.py menu commands -> lo/ (insert, edit data)
```

Everything in `core/` is unit-tested with pytest; `lo/` gets `tests/lo/` scripts run by `test-lo`.

## Steps (each ends green: `check`, and `test-lo` from step 4)

Done: 1-5 (2026-10-28). Undo grouping, planned for step 6, was pulled into step 4: API shape inserts
are not recorded by LibreOffice, so `lo/undo.py` registers explicit undo actions.

Step 5 deviations: no debounce (Calc reports committed edits only, and syncing immediately keeps
the Calc document unmodified, so closing it never asks to save); no double-click yet (Impress uses
it to enter the group), a menu command "Edit chart data" instead; the data sheet follows the
presentation's visibility (hidden presentation -> hidden Calc document).

1. `core/model.py`, `state_io.py` with schema v1 and round-trip/validation tests.
2. `core/datasheet.py`: table parsing incl. empty cells, text in number cells, extra rows; raw
   cells (formulas) and evaluated values kept side by side.
3. `core/layout/column.py`: stacked and clustered, uses `scale.nice_axis`; golden-geometry tests.
4. `lo/render.py` + `lo/store.py`; "Insert column chart" with sample data. `tests/lo`: insert, save as
   ODP and PPTX, reload, state found. (Turns the spike into a regression test.)
5. `lo/datasheet.py`; "Edit data"; `tests/lo`: change a cell, group children update; enter a
   formula, close, reopen the data sheet, formula is still there.
6. Duplicate-id fork and orphan message; undo grouping; manual test of copy/paste in the real UI.
7. ADRs 0004-0006, ARCHITECTURE.md, glossary (chart id, chart state, orphaned chart), CHANGELOG, delete this plan.

`test-lo` in CI is tracked separately (needs LibreOffice >= 25.8 on the runner).

## Decisions by the maintainer (2026-10-28)

1. PPTX round trip is a **hard requirement** -> Decision 1 as recommended.
2. Orphaned charts after copying into another document: **acceptable for M1**, with a clear message.
3. Formulas: **persisted** (see Decision 2).
4. Re-layout on resize: **later**; M1 re-layouts only on data changes, using the group's current size.

## Out of scope for M1

Labels beyond value labels, legends, axis break, number formats, styling UI, waterfall/Mekko.
