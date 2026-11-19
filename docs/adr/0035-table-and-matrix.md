# 0035. Table and 2x2 matrix as chart kinds

- Status: accepted
- Date: 2026-11-20

## Context

A styled table and a 2x2 matrix are slide elements that need a data editor, persistence, resize,
undo and PPTX survival. A native Impress table cannot carry Harvey balls or sparklines reliably;
duplicating the chart lifecycle would be worse.

## Decision

- **A table is a chart kind** (`kind="table"`) whose data sheet is the cell grid. Table options
  (`TableSpec`: header, first column, zebra, borders, heatmap, widths, row height) live in the
  chart state.
- **Typed cells** are text markers: `{harvey:75}`, `{check:tick}`, `{spark:1,3,2}`. `{{` escapes a
  literal brace. Numbers come from Calc; text stays text.
- **A matrix is a chart kind** (`kind="matrix"`) with fixed columns `Label | X | Y | Size | Group`
  and a `MatrixSpec` for titles, end labels, quadrants and splits.
- Both reuse insert, store, render, resize, data sheet and undo. They reject chart-only options.
- Schema 20 adds the two specs; a kind without a spec gets the default spec.

## Consequences

The Calc data sheet remains the editor; no second table editor is introduced. Merged cells and
rich text stay out of scope. The heatmap uses palette entries, so a corporate scheme applies.
