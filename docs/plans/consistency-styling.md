# Plan: M8 consistency and styling

Status: draft, not yet agreed (2026-10-29). Builds on M6 (`Format`, `core/style.py`).

## Goal

The features empower and think-cell offer for decks with many charts:

- **Same scale**: several charts show the same value with the same length, so their columns can
  be compared across charts and slides.
- **Colour schemes**: a document-wide scheme (palette, text and line colour, font) instead of the
  fixed constants in `lo/render.py`; built-in schemes plus a corporate design loaded from a file.
- **Series colours**: single series of a chart can get another colour of the scheme.
- **Copy chart format**: take the format of one chart and apply it to other selected charts.

Non-goals: per-segment colours, gradients and patterns, a full colour picker, a template gallery.

## Approach

### Colour schemes (`core/style.py`, `lo/render.py`, new `lo/scheme.py`)

- `Scheme(name, palette, text, line, background, font_name, font_size)` in `core/style.py`, plus
  three built-in schemes (today's colours as "Default", a grey one, a high-contrast one).
  JSON (de)serialisation with a version, like `state_io.py`.
- The document scheme is stored as a document custom property `librecharts:scheme` (same storage
  as chart states, ADR 0004). No property: the "Default" scheme, so existing documents keep their
  look.
- `render.py` takes a `Scheme` instead of module constants; M6's `text_color` uses the scheme's
  palette. Changing the scheme redraws every LibreCharts chart in the document in one undo step.
- Corporate design: "Load colour scheme..." / "Save colour scheme..." read and write the JSON
  through the file picker; "Use for new presentations" stores it in the extension's configuration
  (new `extension/Config.xcs`/`.xcu`, user profile), applied when a presentation without a scheme
  gets its first chart.

### Series colours (`core/model.py`)

- `ChartState.colors: tuple[int | None, ...]`: per data sheet row the index of a scheme colour,
  `None` for the default (row index modulo palette length). Indices shift with inserted rows like
  annotations (M7 open question 5 applies the same way).
- Pick command `PickSeries?as=color` (shared with M7): click a segment, then a submenu with the
  scheme's colours (named "Colour 1".."Colour n", no picker dialog, testable headless).
- Schema version 8; migration adds `colors: []` and `scale_group: null` (below).

### Copy chart format (`lo/commands.py`, `core/format.py`)

- "Copy chart format" stores the selected chart's `Format` (M6) and `colors` in a per-process
  slot in `lo/`; "Apply chart format" applies it to every selected chart (multi-selection) in one
  undo step. Data, kind, variant and annotations are not copied.
- `core/format.py`: `apply(target, source) -> ChartState`, so what is copied is tested in `core/`.

### Same scale (`core/samescale.py`, `lo/samescale.py`)

- `ChartState.scale_group: str | None`: charts with the same id share a scale. "Same scale" with
  two or more charts selected gives them a new id; "Remove same scale" clears it on the selected
  chart.
- `core/samescale.py`: `length_per_unit(state, width, height) -> float` is the natural scale of one
  chart; the group uses the smallest one (so the chart with the largest values still fits).
  `layout_chart(..., length_per_unit=None)` draws with a given scale; the plot then does not fill
  the chart's height. Only the geometry changes, never the structure (ADR 0007).
- Kinds: column, bar, waterfall, units Mekko, line, area. 100 % charts and percent Mekkos cannot
  join a group (the menu entry is disabled for them).
- `lo/samescale.py`: after every change of a chart in a group (data sheet edit, option, resize,
  removing a chart) the other charts of the group anywhere in the document are laid out again.
  All of them go into the same undo action (`lo/undo.py` gets a multi-group action). The resize
  watcher calls it after its own re-layout.
- A copied chart keeps the group id (copies within a deck should compare); `claim` forks only the
  chart id.

### UI

- Context menu: "Same scale" / "Gleiche Skalierung" (with several charts selected), "Remove same
  scale", "Copy chart format", "Apply chart format", "Series colour" (pick).
- Sidebar: a "Document" section with the scheme selection (built-ins, load, save) and the
  same-scale and format-copy buttons.
- Multi-selection: today's commands work on one selected chart; `lo/commands.py` gets a helper for
  "all selected LibreCharts charts".

## Affected modules

`core/style.py`, `core/model.py`, `core/state_io.py`, `core/format.py`, new `core/samescale.py`,
`core/layout/*` (given scale), `core/menu.py`, `core/panel.py`, `core/messages.py`,
`lo/render.py`, new `lo/scheme.py`, new `lo/samescale.py`, `lo/undo.py`, `lo/resize.py`,
`lo/datasheet.py`, `lo/commands.py`, `lo/sidebar.py`, `lo/pick.py`, `extension/entry.py`,
`extension/Config.xcs` / `.xcu` (new), `extension/manifest.xml`.

## Tests

- `tests/core`: scheme JSON round trip, version errors, built-ins valid; default scheme gives
  today's colours; `colors` migration and dangling indices; `apply` copies format and colours only;
  common scale of a group (smallest wins, percent charts excluded); layout with a given scale has
  the same structure and proportional heights.
- `tests/lo/test_scheme.py`: set a scheme -> all charts redrawn, one undo; scheme survives ODP
  reload (PPTX: the shapes keep their colours, the scheme property is dropped; to verify).
- `tests/lo/test_same_scale.py`: two charts on two slides, data edit in one rescales the other,
  one `.uno:Undo` restores both; resize; copy keeps the group.
- File picker and colour submenu look: by hand.

## Docs

New ADRs "Colour schemes" and "Same scale"; ARCHITECTURE.md (new modules, scheme storage);
glossary ("Colour scheme", "Same scale", "Scale group", "Chart format"); CHANGELOG; ROADMAP;
README.

## Open questions (recommendation first)

1. One scheme per document (recommended: corporate design is consistent per deck) or a scheme
   per chart.
2. Series colours from the scheme only (recommended) or any RGB colour through LibreOffice's
   colour dialog (not testable headless).
3. Same-scale groups span the whole document (recommended) or one slide.
4. Axis breaks in a scale group: the break is ignored for the common scale and not drawn
   (recommended), or the group scale is computed on the folded values.
5. A default scheme for new presentations in the extension configuration (recommended) or only
   load/save per document.
