# Architecture

A map of the code and the rules that keep it testable. Decisions and their reasons live in
[docs/adr/](docs/adr/); terms in [docs/glossary.md](docs/glossary.md).

## Layers

```
LibreOffice Impress
   │  menu / dispatch
   ▼
extension/entry.py          UNO protocol handler. Thin: translate a command into a call to lo/.
   │
   ▼
src/librecharts/lo/         UNO adapter. Builds shapes from core models, talks to Calc, reads
   │                        the document. The only package (besides extension/) allowed to import uno.
   ▼
src/librecharts/core/       Pure Python. Chart models, layout, axis scaling. Input: numbers and
                            sizes. Output: plain geometry (rectangles, lines, text positions).
```

Dependencies point downward only: `core` knows nothing about `lo` or `extension`.

## Modules in `core/`

| Module | Role |
|---|---|
| `model.py` | `ChartState`: the persisted description of a chart (raw cells, evaluated values, kind, grouping, annotations, Mekko/100 % option `percent`, category `sort`, `format`, line series `lines`/`secondary`, series palette overrides `colors`, same-scale group `scale_group`, data `link`, schema version) |
| `format.py` | Chart format options: defaults for a new chart, `ChangeFormat` arguments, which chart kind supports what, number-format parsing and validation, locale rules, `apply` for "copy chart format" (ADR 0014) |
| `style.py` | Colour schemes (palette, text, line, background, font), the built-ins, scheme JSON and the black/white text colour for a fill by WCAG relative luminance (ADRs 0014, 0016) |
| `samescale.py` | Same-scale groups: orientation, joinability, the natural length per value unit of every layout and the smallest common one (ADR 0017) |
| `value_line.py` | Value lines: the average of a chart, the level a line marks, validation of the dialog's value or date (Gantt date lines) |
| `annotations.py` | Which annotations a chart kind supports, the values and labels of arrows, command arguments (ADR 0010) |
| `axis_break.py` | The axis break: automatic or manual value range to remove from the scale, `fold`, validation of the dialog's input |
| `options.py` | Chart options the user can switch after inserting (variants, 100 %, sorting, Mekko percent/units, line series and their axis): the switches offered for a chart and the `ChangeChart` command's arguments (ADRs 0012, 0013, 0015) |
| `percent.py` | Shares and the "negatives count as empty" rule for 100 % charts and the Mekko |
| `sorting.py` | Display permutation of the categories, reordered data and annotation indices (ADR 0013) |
| `picking.py` | Pick mode: chart point -> column or line point, `PickSession` collects the picks for one annotation |
| `links.py` | Data links: range addresses and names, relative and absolute source URLs, the fetched grid (names as shown, values as numbers), the read-only view, update reports (ADR 0020) |
| `menu.py` | Contents of the chart's context menu as plain data |
| `panel.py` | Contents of the sidebar panel (buttons, status, annotation list) as plain data |
| `state_io.py` | `ChartState` <-> JSON with schema migrations; malformed input raises `StateError` |
| `messages.py` | All user-visible strings in English and German (a test enforces both) |
| `datasheet.py` | Data sheet conventions: cell grid -> `ChartData` (categories, series); sample data |
| `scale.py` | "Nice" value axis ranges |
| `primitives.py` | `Rect`, `Line`, `Polyline`, `Polygon`, `Marker`, `Bubble`, `Text`: layout output in 1/100 mm, styling left to the renderer (`BACKGROUND` and `SHADE` fills, bold `heading` text) |
| `elements.py` | Harvey ball and check mark names (state in the group name, ending in a letter), the cycle of states and the primitives of each (ADR 0021) |
| `arrange.py` | Geometry of same width / height / size, grid and swap on rectangles |
| `geometry.py` | Circle geometry: `polar` and `sector` (pie and doughnut segments as point lists; shared with the Harvey balls of M12) |
| `gantt.py` | Gantt data sheet rules (one row per activity; label, start, end, remark, phase by column position) -> rows of type bar, milestone, phase or heading; Calc serial numbers <-> dates; sort by start (ADR 0019) |
| `timescale.py` | The Gantt date scale: unit pair from the date range, periods, header labels and date texts per language |
| `scatter.py` | Scatter data sheet rules (one row per point; label, x, y, size, group by column position) -> points and groups (ADR 0018) |
| `layout/column.py`, `layout/bar.py` | `ChartData` + size -> primitives for stacked, clustered and 100 % columns / horizontal bars; columns also draw annotations and line series on a secondary axis |
| `layout/line.py` | Points at the category centres, one `Polyline` per run of values, markers, a label at every point and the series names right of the last point |
| `layout/area.py` | Stacked and 100 % areas: one `Polygon` per series between its cumulative edges, labels inside, series names right of the last category |
| `layout/pie.py` | Pies and doughnuts: one pie per category, one `Polygon` per segment clockwise from 12 o'clock, shares inside or outside by angle, the sum in a doughnut's hole |
| `layout/scatter.py` | Scatter and bubble charts: forced axes without zero, `Marker`s or `Bubble`s, group legend, value line |
| `layout/gantt.py` | Label column, two-level date header, a band per row with bars, milestone diamonds and phase brackets, remarks, shading, gridlines and date lines |
| `layout/butterfly.py` | Two series as bars mirrored around a band of category names, one common scale, optional axis and gridlines |
| `waterfall.py` | Waterfall data sheet rules (value row, "Total" marker row) -> steps with running totals |
| `layout/waterfall.py` | Steps -> floating bars, totals, connectors and signed labels |
| `mekko.py` | Mekko data sheet rules (optional "Width" row, negatives ignored) -> segments and column widths |
| `layout/mekko.py` | Variable-width columns, 100 % high (percent) or scaled by their sums (units); value, total and width labels, series names |
| `layout/common.py` | Number format, value axis and gridlines, series labels and legend, value-line lanes shared by the layouts |
| `layout/chart.py` | `layout_chart(state, w, h, length_per_unit=None)`: applies sorting, picks the layout by chart kind and passes the shared scale of a same-scale group (ADR 0017) |

Data flow: Calc cells -> `ChartState` (stored in the document) -> `datasheet.parse` -> `ChartData`
-> `layout_column` -> primitives -> `lo/` draws shapes. Stored state is part of the user's files,
so every released schema version must stay readable (`state_io.py`).

## Invariants

1. **`core/` never imports `uno`.** Enforced by ruff (`TID251`) so that the layout logic is unit-testable
   without LibreOffice.
2. **No runtime dependencies.** Everything ships inside the `.oxt` and runs on LibreOffice's bundled
   Python (ADR 0001).
3. **A chart is a group of native Draw shapes** (ADR 0002); the slide still looks right if the
   extension is not installed.
4. **Layout is a pure function** of chart data, available size and the optional shared scale: same
   input, same geometry. The kinds and order of primitives depend on the data only, never on the
   size (ADR 0007).
5. **The chart state in the document is the truth; the Calc data sheet is a view** (ADRs 0003, 0005).
   State lives in a document property anchored by the group name (ADR 0004, schema in ADR 0006).

## Modules in `lo/`

| Module | Role |
|---|---|
| `store.py` | Chart id anchor (group name `librecharts:<id>`), state in a document custom property, the document's colour scheme property, `claim` forks renamed copies; no `uno` import, unit-tested with fakes |
| `render.py` | Primitives -> shapes in a group with a `Look` (scheme plus series colours); `rerender` replaces children in place, `sync_geometry` moves them for a resize (poly shapes through `PolyPolygon`) |
| `scheme.py` | Reads and writes the document's colour scheme; the configured default for new documents; builds the renderer's `Look` (ADR 0016) |
| `samescale.py` | Collects a scale group's charts and sizes, redraws every affected chart in one lock (ADR 0017) |
| `undo.py` | One explicit undo action per chart operation |
| `elements.py` | Harvey balls and check marks: find, insert, change state (one undo step), re-lay out after a resize; the state is the group name (ADR 0021) |
| `arrange.py` | The selected shapes and the undo action for same size, grid and swap; the geometry is `core/arrange.py` |
| `chart.py` | Insert (with the UI locale for number formats), `redraw`, `add_annotation`, `apply_changes`, `set_scheme`, `fit_to_size`: chart operations on a presentation |
| `datasheet.py` | Calc window as a transient view: write stored cells (Gantt date columns in a date format), sync every committed edit back; a protected read-only view for linked charts |
| `links.py` | Data links: find, open (hidden, read-only, no macros) and read the sources of linked charts, each once per update; the info bar when sources changed (ADR 0020) |
| `linkdialog.py` | The link dialog (modal, built in code): file, sheet, range or name; reads the range before it links |
| `commands.py` | Menu commands (selection handling, messages, same scale, copy format, scheme files, data links); called by `extension/entry.py` |
| `resize.py` | One watcher per presentation: after a resize, re-lays charts out in place, including their scale group (ADRs 0007, 0017) |
| `doubleclick.py` | One mouse click handler per presentation: double-click on a chart opens its data sheet |
| `axisdialog.py` | The axis break dialog (modal, built in code); asks, then adds or changes the break |
| `formatdialog.py` | The number-format and value-line dialogs (modal, built in code); validation lives in `core/format.py` and `core/value_line.py` |
| `pick.py` | Pick mode: enters the chart group, turns selected shapes into an annotation (ADR 0010) |
| `sidebar.py` | The LibreCharts sidebar panel: window with buttons, follows selection and document (ADR 0011) |
| `contextmenu.py` | One interceptor per presentation: the LibreCharts submenu in a chart's context menu |
| `ui.py` | UI locale and message boxes; texts come from `core/messages.py` |

Further invariants of the adapter:

6. **A chart group starts with an invisible frame rectangle** covering the full layout box, so the
   group's size equals the layout size and re-rendering at the current size is stable.
7. **Every chart operation is exactly one undo step.** LibreOffice does not record API shape
   inserts, so `lo/undo.py` locks its recording and registers an explicit action.

8. **The data sheet is a view, the document property is the truth.** Every committed Calc edit
   is stored and redrawn immediately; the Calc document's modified flag is reset after each sync,
   so closing it never asks to save. It is never written to disk.

Update this file whenever a module is added or a boundary changes.
