# 0023. Label placement

- Status: accepted
- Date: 2026-10-29

## Context

M13 lets the user drag single value labels and totals, as in think-cell: a label out of a segment
too flat to hold it, a column total away from an arrow. A moved label has to follow its segment
through data edits, sorting, resizing, copies, data link updates and ODP/PPTX files, and it must
not break the two rules of the adapter: the primitive structure is independent of the size (ADR
0007), and every operation is one undo step (ADR 0003).

A spike against LibreOffice 26.8 showed:

- A shape of an entered group moved with the position dialog (`.uno:TransformDialog`) fires modify
  events and records exactly one undo step; undo and redo restore it. An API move records nothing.
- LibreOffice's undo of a child move or of a group resize refers to the shapes it moved. A later
  redraw that *replaces* the children leaves that step without visible effect. Shapes removed from a
  group and added again lose their geometry, so the steps cannot be rescued by putting them back.
- Resizing a group scales a child outside the frame like every other child; a label moved out of the
  chart (by API) was taken for a resize, because the group's bounding box grew.
- Reading every child of a chart costs milliseconds (17 ms for 122 shapes), too much to do for all
  charts on every modify event. A moved label is selected after the move and after an undo inside
  the group; after leaving the group the undo manager still reports `actionUndone`/`actionRedone`.

## Decision

- **A move is stored as an offset.** `ChartState.labels` holds `LabelOffset(key, dx, dy)`: how far
  the label's *centre* is moved from where the layout puts it, in 1/100 mm, absolute (not scaled on
  resize, like font sizes). `LabelKey(role, category, series)` names the label by its role (`value`
  or `total`) and *data sheet* indices (a `None` series for a total, a waterfall step and a scatter
  point, which is its position among the drawn points), so sorting never touches them. Like
  annotation indices, an offset whose label is gone stays stored and unused: undoing the edit brings
  the label back. Schema version 12.
- **Offsets never change the primitive structure.** The layouts key their value labels and totals
  (in display indices; `layout_chart` maps them to data sheet indices through the sort order) and
  `core/labels.place` moves each keyed label, reveals it, makes its box at least `LABEL_HEIGHT` high
  and takes the text colour from the data shape under its new centre. A label too large for its
  segment now keeps its text and sets `Text.hidden` instead of being emptied; the renderer draws
  it empty. `core/labels.moved` is the reverse step: from the laid-out primitives and the boxes of
  the shapes it returns the new offsets, or `None` if anything but keyed labels differs (a resize, a
  redraw in progress, a bar moved by hand). An offset below 1 mm on both axes is dropped: a label
  dragged back onto its place snaps there.
- **The frame is the layout box.** The invisible frame (invariant 6) stays the layout box while the
  group's bounding box may grow with a label moved out of the chart. Position and size of a chart
  are read from the frame (`render.layout_box`) everywhere: layout, redraw, same scale, picking and
  the watcher, never from the group. For charts without moved labels both are the same.
- **The watcher stores moves without an undo action.** After a change it reads the children of a
  chart only where a label can have moved: the chart whose child is selected, and the charts of the
  current slide after an undo or redo that is not one of ours (an `XUndoManagerListener`). It asks
  `labels.moved`, stores new offsets (`store.write_state`) and syncs the moved labels in place. LibreOffice
  records the drag; its undo moves the label back and the next check clears the offset. Any other
  child that differs from the layout (a series name or axis label dragged by hand, a bar moved in
  pick mode) is put back at once: the chart always matches its layout. `samescale.apply_states`
  marks the document busy while it stores and draws, and the watcher skips a busy document, so a
  redraw that only moves labels (*Reset label positions*) is never read back as a drag.
- **Redraw in place.** `render.rerender` updates the existing shapes (geometry, text and every
  property the renderer sets, one code path for new and existing shapes) when the kinds and order of
  the primitives are unchanged, and replaces the children only otherwise. Value edits, number
  formats, sorting, colours and offsets keep the structure, so LibreOffice's older undo steps keep
  working. This also repairs the undo of a resize after a data edit.
- **Movable and fixed.** Value labels and totals of every chart kind but Gantt are movable. Series
  names, arrow and value-line labels, axis, category and Marimekko width labels and the legend stay
  where the layout puts them.
- **Commands.** *Move labels* enters the chart group (`.uno:EnterGroup`) and shows an info bar
  until the group is left (Esc, or selecting something else); it is built like pick mode. *Reset
  label positions* clears all offsets through `chart.redraw`, one undo step. In pick mode a click on
  a moved label picks the column it belongs to, not the column under its new place.
- **Variants clear the offsets.** Switching the layout variant (stacked, clustered, 100 %, line
  series, Mekko units, doughnut) clears them: places chosen in a stacked chart mean nothing in a
  clustered one. Sorting, number format, scheme, same scale, data edits and link updates keep them.
  *Copy chart format* does not copy offsets: they belong to the chart's data.

## Consequences

- No leader lines from a moved label to its segment: a line that appears with an offset would change
  the primitive structure, so a drag could no longer be stored in place and LibreOffice's undo of
  the drag would refer to a replaced shape. Automatic placement and overlap removal (M16) will move
  labels out of segments itself.
- A scatter point's key is its position among the drawn points: a row that loses its x or y value
  shifts the keys of the points after it.
- Inserting a row or column into the data sheet does not shift offsets (nor annotation indices).
- A hidden label is an empty shape that cannot be clicked, so a label that does not fit its segment
  cannot be dragged out with the mouse until the segment grows.
- After a structural change (a new category, the axis switched on) LibreOffice's older undo steps
  of the old shapes stay without visible effect.
- A real mouse drag, the info bar and the look of *Move labels* are tested by hand; `tests/lo`
  moves labels with the position dialog inside the entered group.
