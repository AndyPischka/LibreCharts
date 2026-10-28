# 0010. Annotations: stored with the chart, placed by picking columns

- Status: accepted
- Date: 2026-10-28

## Context

M4 adds difference arrows (bracket above the columns or level difference right of the plot), CAGR
arrows and axis breaks to column charts. They have to survive data edits, undo, resizing, saving
as ODP and PPTX and copying, like the chart itself. Users place them by clicking columns, as in
think-cell. An extension cannot ask Impress which shape is under the mouse.

## Decision

- **State**: `ChartState.annotations` (schema 2, migrated from 1 by adding an empty list). An
  `Annotation` has a kind, start and end category **indices**, an optional series (one bar of a
  clustered chart; otherwise the column total), and for difference arrows a style (bracket/level)
  and a label mode (percent/absolute). An annotation whose indices no longer exist after a data
  edit stays stored but is not drawn, so undoing the edit brings it back.
- **Layout**: part of the column layout. Every bracket arrow gets a lane above the plot, every level
  arrow a lane right of it; the number of lanes depends on the annotations only (ADR 0007). An
  axis break excludes its column from the scale and draws it from 0.85 to 1.15 times the tallest
  other column, with a white gap; labels keep the real values.
- **Pick mode**: a command enters the chart group (`.uno:EnterGroup`); a click inside then selects
  the shape under the mouse, and a selection listener maps that shape's centre to a column with the
  layout's own geometry (`core/picking.py`). An info bar says what to click; `Esc` or a selection
  outside the chart cancels. The finished annotation is added asynchronously after leaving the group.
- **Context menu**: an interceptor adds a "LibreCharts" submenu to the context menu of a selected
  chart (`core/menu.py` builds its contents): edit data, add annotations, and per annotation
  percent/absolute, bracket/level and remove.
- Every action is an `org.librecharts:` command with URL arguments, so menus, toolbar and tests use
  the same code path. Each change is one undo step.

## Alternatives considered

- **Map mouse pixels to slide coordinates** in a mouse click handler: handler coordinates are
  relative to an inner edit window, and `controller.VisibleArea` did not match its size in tests
  (spike on LibreOffice 26.8). Letting Impress hit-test is exact at any zoom.
- **Annotations in the data sheet** (marker rows like the waterfall's "Total" row): no new UI, but
  hard to discover and unwieldy with several arrows.
- **A dialog** with start and end columns: simpler to test, but further from think-cell's way of
  working; the user chose clicking.
- **Category names instead of indices** as references: names may repeat or be empty.

## Consequences

- Inserting or deleting a column in the data sheet shifts what an annotation points at.
- In pick mode a drag moves a bar; there is no mouse motion handler in Impress to prevent it. The
  redraw after the pick replaces the children anyway.
- The context menu cannot offer actions for the right-clicked column, only for the whole chart.
- Axis break gaps are white; on a coloured slide background they show.
- Only column charts have annotations so far; bar and waterfall charts can follow with the same
  state and pick mode.
- Arrow labels are locale-neutral like all labels (ADR 0006).
