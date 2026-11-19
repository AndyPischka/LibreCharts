# 0036. Layout tools, graphics and icons

- Status: accepted
- Date: 2026-11-20

## Context

Impress's alignment dialogs are slow in a deck workflow, and process, chevron and pyramid graphics
are rebuilt by hand in every presentation. Both are pure geometry and can live in `core/`.

## Decision

- **Arrange commands** extend `core/arrange.py`: distribute with equal gaps or centres, align to the
  selection box, align to slide with a margin. One command is one undo step; the selection order
  never matters (position order does).
- **Graphics are groups** whose state is the group name (`librecharts-graphic:process:4:horizontal`,
  `...:icon:<name>`) plus child text shapes. No document property and no schema bump.
- **Core layout** returns primitives; `lo/graphics.py` inserts, changes and re-fits them. Step
  labels stay editable in place.
- **Icons are drawn from primitives** (arrow, target, warning, check, cross, idea, person, gear,
  calendar, money, chart), so there is no asset licence and corporate colours apply.

## Consequences

The resize watcher tracks graphics like charts and elements. Adding a step keeps existing labels;
removing one drops only the last. A graphic is not a chart: it has no data sheet.
