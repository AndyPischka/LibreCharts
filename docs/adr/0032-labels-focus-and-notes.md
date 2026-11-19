# 0032. Label overrides, focus and chart notes

- Status: accepted
- Date: 2026-11-20

## Context

M13 moves labels, but a deck often needs to hide one label, replace it with a short message, mute
everything that is not the point, or carry a source line. These are chart content, not layout
decisions, so they must survive data edits and sorting like moved labels do.

## Decision

- **The label record grows** (`LabelOffset`: `hidden`, `text`). The key stays `LabelKey`; at most
  one record per key. `place` applies offsets, visibility and text before the renderer runs.
- **Focus is a chart option** (`Focus(series, categories)`), a union: a point stays at full colour
  when its series or its category is focused. Layout primitives carry `category` and `muted`; the
  renderer mixes muted colours towards the background and keeps text contrast.
- **Source and notes are chart content**: `source` is a footer band, notes are anchored at
  fractions of the layout box. Neither is copied by *Copy chart format*.
- **Typography**: `Format.font_size` overrides the scheme font; `Format.legend` is top, right,
  bottom or left. Both are format fields and are copied.
- Schema 17 stores all of it; older labels load visible and unchanged.

## Consequences

Muting is decided in `core/`, so every layout test can check it without LibreOffice. The renderer
needs no knowledge of focus. A note's text box keeps its layout box when dragged; its anchor is
stored as a fraction of the chart box.
