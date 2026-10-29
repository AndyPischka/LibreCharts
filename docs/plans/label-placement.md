# Plan: M13 label placement

Status: agreed with the maintainer on 2026-10-29. Deferred from M6
(`docs/plans/axes-labels-legend.md`, open question 5); M16 (decluttering) builds on it.

## Goal

The user drags single **value labels** to another place, as in think-cell: a label out of a segment
too flat to hold it, a bar's label away from an arrow. The chart remembers every move as an
**offset** from where the layout puts the label, so the label follows its segment through data
edits, sorting, resizing, copies, data link updates and ODP/PPTX files. A label dragged back onto
its place snaps there; one command puts all labels of a chart back.

Movable: the value labels of segments and bars (column, bar, butterfly, Mekko), waterfall steps,
line and area points, pie segments and scatter points. Every other text of a chart (totals, series
names, arrow and value-line labels, axis, category and Mekko width labels, the legend, Gantt
charts) stays where the layout puts it.

Non-goals: leader lines from a moved label to its segment (with M16, see decision 4), automatic
placement and overlap removal (M16), moving totals, series names or annotation labels, editing a
label's text, hiding single labels, label position options (inside/outside/above) per series.

## Approach

### State (`core/model.py`, `core/state_io.py`, new `core/labels.py`)

- `LabelKey(category, series)`: names a value label by **data sheet** indices, independently of
  size and display order. `series` is `None` where a label belongs to a category or row alone (a
  waterfall step, a scatter point).
- `LabelOffset(key, dx, dy)`: how far the label's **centre** is moved, in 1/100 mm, absolute: not
  scaled on resize, like font sizes. `ChartState.labels: tuple[LabelOffset, ...]`, at most one per
  key.
- Indices behave like annotation indices (ADR 0010): sorting never touches them, inserting a data
  sheet row shifts them, an offset whose label is gone stays stored and unused, so undoing the edit
  brings it back.
- Schema version 12: `_v11_to_v12` adds `"labels": []`.

### Layout (`core/primitives.py`, `core/layout/`, `core/labels.py`)

- `Text` gets `key: LabelKey | None = None` and `hidden: bool = False`. Layouts give keys to value
  labels, in display indices. A label too large for its segment keeps its text and sets `hidden`
  instead of being emptied; the renderer shows a hidden label as empty, as today.
- `layout_chart` maps the keys' categories back to data sheet indices through the sort order (as
  `picking._to_data_index` does) and applies the offsets with `labels.place`: it moves each keyed
  label by its offset, unhides it, makes its box at least `LABEL_HEIGHT` high around the new centre
  and sets `fill` to the data rectangle under the new centre (its own segment, another one, or none
  for the scheme's text colour), so a label moved out of a dark segment does not stay white.
- Offsets never add, remove or reorder primitives: the structure stays independent of size *and*
  of offsets (ADR 0007), so a move is stored and synced in place.
- `labels.moved(laid_out, current)` is the reverse step for the adapter: given the primitives laid
  out for the current state and the child geometry read from the shapes, it returns the new offsets
  (`old + current centre - laid-out centre`), or `None` if anything but value labels differs (a
  resize, a redraw in progress, a moved bar). An offset below 1 mm on both axes becomes no offset
  (snap back).

### The frame is the layout box (`lo/render.py`)

A moved label may stick out of the chart, and the group's bounding box then grows. The invisible
frame (invariant 6) stays the layout box: `render`, `chart.fit_to_size`, `samescale`, `pick` and the
watcher read position and size from the frame (`render.layout_box(group)`), no longer from the
group. For charts without moved labels both are the same, so existing charts do not change. This
also fixes today's behaviour where dragging any child out of the chart counts as a resize and
re-lays the whole chart out at the larger size.

### Detecting a move (`lo/resize.py`, new `lo/labels.py`)

The watcher already runs (coalesced, asynchronously) after every change of the document. For the
charts on the **current slide** it now:

1. reads the frame; a changed frame size is a resize: `fit_to_size` as today, offsets included;
2. otherwise reads the children's geometry in one pass and asks `labels.moved`; new offsets are
   stored (`store.write_state`, **no undo action**) and the moved labels synced in place (box,
   text, colour; `sync_geometry` learns to sync the text colour);
3. puts back at once any other child that alone differs from the layout: a total, series name,
   axis or annotation label dragged by hand, or a bar moved in pick mode. The chart always matches
   its layout.

Undo follows ADR 0007: LibreOffice records the drag (or arrow-key nudge) as one step; its undo
moves the label back, and the watcher, comparing again, clears the offset. Redo likewise.

Our own redraws never look like a label move: they move bars too, and while children are being
replaced their count does not match. `samescale.apply_states` additionally marks the document busy
while it stores and draws, and the watcher skips a busy document: commands from scripts and tests
run on a bridge thread beside it (AGENTS.md), and comparing old shapes with an already stored new
state (e.g. after *Reset label positions*) would otherwise read the old offsets back.

### UI and commands

- **Move labels** / **Beschriftungen verschieben** in the chart's context menu and the sidebar:
  enters the chart group and shows an info bar ("Drag value labels to move them. Esc ends.") until
  the group is left; built on the group session of `lo/pick.py`, without picks. F3 works as well;
  double-click still opens the data sheet.
- **Reset label positions** / **Beschriftungen zurücksetzen** (`org.librecharts:ResetLabels`):
  clears all offsets of the chart through `chart.redraw`, one undo step; offered when the chart has
  moved labels.
- Pick mode: a click on a moved label picks the column the label belongs to (child index ->
  primitive -> key), not the column under its new place.

### Other operations

- Changing the variant (`ChangeChart`: stacked/clustered/100 %, line series, Mekko units, doughnut)
  clears the offsets: places chosen in a stacked chart mean nothing in a clustered one. Sorting,
  format, scheme, same scale, data edits and link updates keep them.
- *Copy chart format* does not copy offsets: they belong to the chart's data, not its format.
- Copies and forks carry them with the state; PPTX keeps the shapes as drawn and the state in the
  custom property.

## Spike first (LibreOffice 25.8.7 and 26.8)

1. Dragging a child in an entered group, and an API move, fire the document's modify listeners;
   LibreOffice records exactly one undo step for a drag.
2. Undo of a child move after a redraw replaced that child (move label, edit data, undo, undo,
   redo, redo): no crash, and what happens. Resize has the same pattern today (ADR 0007) and no
   test for it. If it misbehaves: a redraw whose primitive structure did not change updates the
   shapes in place instead of replacing them, which keeps LibreOffice's actions valid for most data
   edits.
3. Resizing a group with a child outside the frame scales the frame like every other child.
4. Undoing a label move on another slide switches to that slide (the watcher reads the current
   slide only); otherwise all charts are checked and the cost measured.
5. Cost per modify event of reading every child of five charts with 100 shapes each.

## Affected modules

New `core/labels.py`; `core/model.py`, `core/state_io.py`, `core/primitives.py`, every layout in
`core/layout/` except Gantt (keys, `hidden`), `core/layout/chart.py`, `core/options.py` (variant
change clears offsets), `core/menu.py`, `core/panel.py`, `core/messages.py`; new `lo/labels.py`;
`lo/render.py`, `lo/resize.py`, `lo/chart.py`, `lo/samescale.py`, `lo/pick.py`, `lo/commands.py`,
`lo/contextmenu.py`, `lo/sidebar.py`, `extension/entry.py`, `extension/Addons.xcu`.

## Tests

- `tests/core`: migration v11 -> v12; every value label of every chart kind (except Gantt) has a
  unique key in data sheet indices, also when sorted, and no other text has one; `place` moves,
  unhides, enlarges and recolours; the structure is independent of size and offsets for every chart
  kind; `moved` finds one or several moved labels, returns `None` for a resize and for a redraw
  (bars moved too), snaps below 1 mm; a variant change clears offsets; the menu and panel entries.
- `tests/lo/test_labels.py`: moving a value label child through the API stores its offset; the
  offset survives a data sheet edit, sorting, a resize (the label keeps its distance from its
  segment), ODP and PPTX reload and a copy; a label moved out of the frame: a later resize lays the
  chart out at the frame, not the group; *Reset label positions* is one `.uno:Undo` step; a moved
  total and a moved axis label are put back. API moves are not recorded for undo, so undo and redo
  of a real drag, the info bar and *Move labels* are tested by hand.

## Docs

New ADR "Label placement" (value labels only, offsets per label key, the frame as the layout box,
the watcher stores moves without an undo action and puts other moved children back); ADR 0007 gets
a pointer to it; ARCHITECTURE.md (`core/labels.py`, `lo/labels.py`, invariant 6: the frame is the
layout box); glossary ("Label key", "Label offset"); CHANGELOG; ROADMAP; README; AGENTS.md pitfalls
from the spike.

## Decisions (agreed)

1. A variant change clears the offsets.
2. Any other child dragged inside the chart is put back at once.
3. Only value labels are movable; totals, series names and annotation labels stay fixed.
4. No leader lines in M13: a line that appears with an offset changes the primitive structure, so a
   drag could no longer be stored in place and LibreOffice's undo of the drag would refer to a
   replaced shape. Better with M16, which moves labels out of segments itself.
5. Offsets are absolute and not scaled on resize, like font sizes.
6. Entering the chart: a *Move labels* command with an info bar, plus F3; double-click keeps
   opening the data sheet.
