# 0021. Slide elements and arranging shapes

- Status: accepted
- Date: 2026-10-29

## Context

M12 adds the small helpers of think-cell that are not charts: Harvey balls, check marks, and
commands that arrange shapes (same size, grid, swap). The agenda part of M12 has its own ADR.

## Decision

Taken from the M12 plan, with the recommended answers to its open questions:

- **An element's state is its group name** (`librecharts-element:harvey:50%`,
  `librecharts-element:check:tick`), not a document property. Copies and pasting into other
  presentations need no stored state and no claiming (ADR 0004). Names end in a letter because
  LibreOffice cuts trailing digits off the name of a copy and appends ` 1`; the parser accepts that
  suffix. Group names must survive ODP and PPTX (tested).
- **Rendering reuses the chart pipeline**: `core/elements.py` lays out primitives (`Polygon`,
  `Polyline`), `lo/render.py` draws them into a group with the invisible frame. A Harvey ball is an
  outline circle (`Polygon.outline`: background fill, edge in palette colour 1) plus a sector from
  `core/geometry.py`; a tick or cross is a `Polyline` in a fixed green or red (`POSITIVE`,
  `NEGATIVE`), not in new colour-scheme fields (that would change the scheme file format).
- **Always a circle**: the element is the largest square that fits the group's box, centred. The
  resize watcher calls `lo/elements.fit_to_size` for every element on every change; the check is
  idempotent and cheap, and sizes cannot be tracked because elements share their names.
- **Changing states** is a context menu on the selected element and a "next state" command that
  cycles, for several elements at once, one undo step. A state of the other kind is ignored.
- **Arranging** is pure geometry on rectangles (`core/arrange.py`): same width / height / size use
  the largest selected shape (UNO does not report the click order), the grid keeps the selection's
  top-left corner and reading order, swap exchanges the centres. `lo/arrange.py` applies the result
  with one explicit undo action; charts in the selection are laid out again by the resize watcher.
- **No grid dialog**: the grid commands offer 2, 3 and 4 columns with a gap of 5 mm. `columns` and
  `gap` (1/100 mm) can be passed in the command's query for other values.

## Consequences

- Elements have no stored state, so they cannot carry more than their name says; a size, colour or
  line width the user changes by hand is replaced when the element is next re-laid out.
- Menu, context menu and sidebar offer the commands; there are no toolbar icons yet.
- Symbols in table cells or text are not supported (non-goal of the plan).
