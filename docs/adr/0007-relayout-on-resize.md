# 0007. Re-lay out resized charts in place, triggered by a document watcher

- Status: accepted
- Date: 2026-10-28

## Context

Resizing a chart group in Impress scales all its shapes: fonts stay, but bars, label boxes and gaps are
stretched. think-cell re-lays the chart out for the new size instead. The re-layout must not break
undo and redo of the resize, which LibreOffice records itself.

Measured with LibreOffice 26.8:

- The document's modify listeners fire on every resize, from the UI and through the API.
- Geometry changes through the API create no undo action.
- Undo of a group resize (`.uno:TransformDialog`) restores the group *and each child shape* to its
  previous geometry; redo restores the geometry the children had when undo was invoked.
- Document-event jobs (`Jobs.xcu`, `onDocumentOpened`) run for visible documents only.

## Decision

- `layout_column` returns the same kinds of primitives in the same order for any size (a too flat
  segment gets an empty label instead of none).
- `lo/resize.py` keeps one watcher per presentation, registered by a document-open job and by the
  insert command. Modify events are coalesced into one asynchronous callback (`AsyncCallback`), so the
  document is never changed inside its own notification.
- The callback looks only at charts whose group size changed since it last looked, lays them out for
  the current size and moves the *existing* shapes (`render.sync_geometry`). No undo action is added:
  LibreOffice's own resize undo restores those very shapes.
- Comparing shapes with the layout makes the check idempotent: after undo, redo or a reload the shapes
  already match and nothing changes. Groups shrunk below the minimum layout size stay stretched.

## Alternatives considered

- **Replace the children on resize** (like a data change): LibreOffice's resize undo would then refer to
  shapes that are no longer in the group.
- **Add an own undo action for the re-layout**: two undo steps per resize, and an action added while
  undoing would clear the redo stack.
- **Change the document synchronously inside the modify notification**: re-entrancy into the drawing
  layer during its own broadcast.
- **Global event broadcaster instead of a job**: would also see hidden documents, but needs its own
  start-up hook; hidden documents are not resized by hand.

## Consequences

- Hidden documents (macros, tests) are watched only after a LibreCharts command ran in them.
- Integration tests must trigger undo and redo through `.uno:Undo`/`.uno:Redo`: `XUndoManager.undo()`
  called from another process made LibreOffice abort intermittently while the watcher was active.
  `tests/test_lo_conventions.py` enforces this.
- Any future layout must keep its primitive structure independent of the size.
