# 0016. Colour schemes and series colours

- Status: accepted
- Date: 2026-10-29

## Context

Every shape colour, the font and the line colours were constants in `lo/render.py`. A deck with many
charts therefore could not follow a corporate design, and two charts side by side could not be
recoloured consistently. The M8 plan asked for a document-wide scheme (palette, text and line
colour, background, font), built-in schemes and a corporate design loaded from a file, plus a way to
give single series another colour of the palette.

## Decision

Agreed with the maintainer in `docs/plans/consistency-styling.md` (recommended answers to its open
questions):

- **`Scheme`** in `core/style.py`: `name`, `palette`, `text`, `line`, `background`, `font_name`,
  `font_size`. It validates its fields and offers `color(series, overrides)`, `grid()` (the line
  colour mixed far towards the background) and `text_on(fill)` (WCAG contrast). Three built-ins:
  `Default` (the old constants), `Grey` and `High contrast`.
- **One scheme per document**, stored as the custom property `librecharts:scheme` next to the chart
  states, so it survives ODP and PPTX. `lo/store.py` excludes it from the chart-id scan. A document
  without the property uses `DefaultScheme` from the extension configuration
  (`/org.librecharts.Settings`, `Config.xcs`/`Config.xcu`), falling back to `Default`.
- **Scheme files** are the same JSON with `"v": 1` (`scheme_to_json`/`scheme_from_json`). Missing
  optional fields fall back to the defaults, so a corporate file only needs its palette. A newer
  version raises `SchemeError`; loading and saving use LibreOffice's file picker.
- **Rendering** takes a `render.Look` (scheme plus the chart's series colours) instead of module
  constants. Text on a filled segment keeps black/white contrast, all other text uses `scheme.text`.
- **Series colours**: `ChartState.colors: tuple[int | None, ...]` holds palette indices per series
  (`None`: the series' own palette entry). Schema version 8 adds `colors: []` and
  `scale_group: null`. The context menu gets "Series colour" with a submenu per series and one entry
  per palette colour plus "Default colour"; a click dispatches
  `ChangeChart?color=<series>&palette=<index|default>`, one undo step. Waterfall colours mean
  increase/decrease/total, not series, so the waterfall has no series-colour menu.
- **Changing the scheme** redraws every chart in the document and is one undo step. Series colours
  are palette indices, so they follow a new palette without being rewritten.
- **Copy chart format** copies `Format` and `colors` (`core/format.py:apply`), never the data, kind
  or annotations. The slot lives in the LibreOffice process (`lo/commands.py`), so the menu and the
  sidebar share it; applying to a multi-selection is one undo step.

## Alternatives considered

- **A scheme per chart**: charts of one deck would drift apart; the plan explicitly wants one
  document-wide look.
- **A full colour picker**: a picker cannot be tested headlessly and invites inconsistent decks;
  palette entries are enough for series and a file covers corporate designs.
- **Gradients and patterns**: think-cell-style charts are flat; they would complicate contrast and
  the primitive model without serving the M8 goal.
- **The document theme of LibreOffice**: it is not exposed reliably to Draw shapes and does not
  travel through PPTX.
- **Storing the resolved RGB colours per series**: a later scheme change would leave old colours
  behind; indices keep charts tied to the palette.

## Consequences

- Schema 8 documents cannot be read by older builds; their shapes still display.
- `Scheme` is pure Python and fully testable; the adapter only reads and writes the document
  property and the file. A scheme file is a stable, human-readable interchange format.
- `render.sync_geometry` does not change colours; a scheme change replaces the children through
  `rerender`, which is why it redraws all charts rather than moving shapes.
- Contrast text stays black or white independent of the scheme; a scheme with an unusual `text`
  colour still keeps labels readable on filled segments.
- The configured default applies to new presentations (no property yet); once a document stores a
  scheme, changing the configuration no longer affects it.
