# M25: Table, 2×2 matrix and heatmap

- Status: proposed
- Milestone: M25 (6.0)
- Builds on: M1 (data sheet, state storage, ADR 0003/0004), M12 (Harvey balls and check marks,
  ADR 0021), M18 (deck specification, ADR 0028), M20 (patterns, ADR 0030)
- Decision: new ADR for a table that is a chart-like group and for the matrix kind

## Goal

Two of the most common consulting slide elements are still missing: a styled table with symbols and
sparklines, and a 2×2 matrix. Both can reuse the machinery that already makes charts work: a group of
native shapes, state in a document property, a Calc data sheet as the editor, one undo step per
operation and a layout that reflows on resize.

## Table

### Architecture decision

Three options were considered:

1. **A native Impress table.** Best text editing, but a Harvey ball or sparkline inside a cell has to
   be an overlaid shape that does not follow column widths or row heights. Resize and undo become
   unreliable, and the corporate design check cannot see the cells as one object.
2. **A shape-based table as a new chart kind (`kind="table"`).** Every cell is a rectangle or text
   primitive in a group, so the existing `store`, `render`, `resize`, `undo`, `doubleclick`,
   `datasheet` and `deck` paths apply unchanged. Editing happens in the Calc data sheet, like chart
   data. Column widths and styling live in the chart state.
3. **A separate table state and adapter.** Cleaner names, but it duplicates the chart plumbing.

The plan proposes option 2. "Table" becomes a chart kind whose `ChartData` is the cell grid. A table
is conceptually a chart that draws text instead of bars, and the existing lifecycle is exactly what
it needs.

### Data and rendering

- The data sheet follows the category/series grid: first row headers, first column row headers, the
  rest cells. `core/datasheet.parse` already returns this shape; a table layout reads the raw strings
  from `state.cells`, not only the evaluated numbers, so text and formulas in header cells work.
- Cell values may be typed markers:
  - `{harvey:75}` draws a Harvey ball at 75 % (0, 25, 50, 75, 100).
  - `{check:tick}`, `{check:cross}`, `{check:empty}` draw the existing check marks.
  - `{spark:1,3,2,5,4}` draws a sparkline scaled to the cell, with an optional last-point marker.
  - Everything else is text. A literal string that starts with `{` can be escaped as `{{`.
- Numbers are formatted with the chart's `Format` (decimals, magnitude, unit, separator). A number
  cell is right-aligned; text is left-aligned; markers are centred.
- `TableSpec` in the chart state:
  - `header: bool` (first row is a header), `first_column: bool` (first column is a row header),
    `zebra: bool`, `borders: bool`, `heatmap: bool`.
  - `widths: tuple[float, ...]` relative column widths (normalised; empty means equal).
  - `row_height: float | None` (absolute, 1/100 mm; `None` distributes the available height).
  - `heatmap_palette: tuple[int, int]`? Better derive a ramp from the scheme so corporate colours
    apply. v1 uses the scheme's line colour mixed into the background; an explicit two-colour ramp
    is a later option.
- Heatmap: numeric cells get a fill between the scheme background and a light scheme colour by their
  value within the visible min/max; text switches to black/white by contrast. Non-numeric cells keep
  the normal fill. The min/max are the data range; an optional fixed range is a later option.
- Borders: horizontal and vertical lines in the scheme line colour, header separated by a thicker
  line. No rounded corners, merged cells or rich text in v1.
- Resize: column widths stay relative, row heights divide the available height, text boxes get the
  cell size. The primitive structure is independent of size (ADR 0007).
- Empty cells still draw their background and border, so the table keeps its shape.

### Editing and commands

- *Insert table* creates a 4×4 sample table with a header and one marker of each kind in the last
  column? Better: a plain 4×4 header + text sample; markers are documented in the help text and the
  data sheet.
- Double-click opens the Calc data sheet through `lo/doubleclick.py`, exactly like a chart.
- Context menu: table options (header, first column, zebra, borders, heatmap), column width
  commands? Widths are hard to edit without a grid UI. v1 offers *Equal column widths* and
  *Fit columns to content* is a later item; the default is equal and the user can edit the JSON
  state only through the sidebar? That is not acceptable. Add a small *Table...* dialog with
  checkboxes and a comma-separated width list. Keep it simple.
- Undo: every option change is one `ChangeTable` command with one undo action, like `ChangeFormat`.

### Table under a chart (stretch)

- Once the standalone table works, a chart can show its own data as a table below the plot:
  `ChartState.data_table: bool` reserves a footer band and reuses the table cell renderer for the
  chart's categories and values.
- The plot shrinks accordingly; the primitive structure still depends on data, not on size.
- This is a stretch goal. If it destabilises the chart layouts or the table renderer, it moves to
  the research list; the standalone table can already be placed under a chart by hand.

## 2×2 matrix

### Data and rendering

- New `kind="matrix"`, data sheet by fixed column position like scatter:
  `Label | X | Y | Size | Group`. `Size` is optional (bubble), `Group` optional (colour).
- The layout draws a plot box with a vertical and a horizontal quadrant line, optional numeric axis
  ticks, and a label in each quadrant.
- `MatrixSpec`:
  - `x_title`, `y_title`, `x_low`, `x_high`, `y_low`, `y_high` (axis end labels, e.g.
    "low cost" / "high cost"), each at most 40 characters.
  - `quadrants: tuple[str, str, str, str]` for top-left, top-right, bottom-left, bottom-right.
  - `x_split`, `y_split`: optional numeric split; `None` uses the middle of the data range.
  - `bubbles: bool` (size column used) and `labels: bool`.
- Points are bubbles or markers; labels sit next to the point and use the existing collision handling
  where possible. A point outside the split range is clamped to the plot and marked? Better reject
  in the data sheet? No: clamp and show a small arrow? Keep it simple: the axes cover the data range
  or the manual split range, whichever is wider.
- The matrix has no categorical axis, no stacking, no annotations in v1. Difference arrows between
  points are a later extension; the scatter layout already knows how to place them, so the matrix
  can inherit that once its hit-test exists.
- Orientation is fixed (x right, y up). A transposed variant is a later option.

## Data model

- `ChartKind` gains `"table"` and `"matrix"`.
- `ChartState.table: TableSpec | None` and `ChartState.matrix: MatrixSpec | None`; validation requires
  the matching kind and rejects the other chart-only fields (`percent`, `sort`, `range`, `errors`,
  lines, annotations, labels) for tables and matrices. `grouping` stays `"stacked"`.
- `Format` applies to both: number format for table/matrix labels, font size (M22) and series names
  only where meaningful. `format.supports` gets explicit table/matrix rules.
- Schema version bump and migration; no old state has the new kinds.
- `core/table.py`: parse typed cells into `Cell` variants (`text`, `number`, `harvey`, `check`,
  `spark`), validate marker syntax, compute column widths and heatmap values.
- `core/matrix.py`: parse fixed columns into points, groups and the split range.

## Approach

1. **Table first, as a chart kind.** Add `kind="table"`, `TableSpec`, `core/table.py` and
   `core/layout/table.py`. Reuse the chart insert, store, render, resize, undo and data sheet paths;
   the only new adapter code is the table dialog and menu entries.
2. **Markers and heatmap.** `core/table.py` emits the same primitives as `core/elements.py` for
   Harvey balls and checks, and a small `Polyline`/`Marker` for a sparkline. Heatmap fills are
   `Rect`s with a `series` index? A per-cell colour cannot be expressed by the series palette. Add a
   `fill: int | None` override to `Rect` or a new `Cell` primitive. Prefer an explicit `fill` field
   on `Rect` (absolute RGB), because the renderer already has a `Look` and can use it.
3. **Matrix second.** Add `kind="matrix"`, `MatrixSpec`, `core/matrix.py` and
   `core/layout/matrix.py`. Reuse the scatter scale, markers/bubbles, label placement and axis
   helpers. Add quadrant lines and four labels.
4. **Commands and UI.** `InsertChart?kind=table` and `?kind=matrix`; a *Table...* dialog for style
   and widths; a *Matrix...* dialog for titles, quadrant names and splits. Each change one undo step.
   Table/matrix entries in the menu, toolbar and sidebar, with icons.
5. **Data sheet and deck specification.** `lo/datasheet.py` is reused as is. `core/deck.py` accepts
   the new kinds and their specs, so a deck can be built from JSON with a table and a matrix.
6. **Alt text and CSV.** A table's description lists its headers and a compact row summary; a matrix
   describes its quadrants and points. CSV export writes the raw cell grid (markers included) like a
   chart's data sheet.

## Affected modules

| Module | Change |
|---|---|
| `core/model.py` | New kinds, `TableSpec`, `MatrixSpec`, validation, schema version |
| `core/state_io.py` | Migration |
| `core/table.py`, `core/matrix.py` | New parsers and validation |
| `core/layout/table.py`, `core/layout/matrix.py` | New layouts |
| `core/layout/chart.py` | Dispatch |
| `core/primitives.py` | `Rect.fill` override for heatmap cells (or a cell primitive) |
| `core/format.py`, `core/options.py` | Supported format/options per kind |
| `core/alttext.py`, `core/csvexport.py` | Descriptions and export |
| `core/deck.py`, `core/cli.py` | New kinds and specs |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Insert entries, table/matrix dialogs texts |
| `lo/chart.py`, `lo/commands.py`, `lo/doubleclick.py` | Insert, redraw, edit |
| `lo/render.py` | Absolute fill for heatmap cells |
| `lo/tabledialog.py`, `lo/matrixdialog.py` | New modal dialogs (logic in core) |
| `extension/Addons.xcu`, `extension/images/`, `extension/description/` | Entries, icons, release notes |
| `tests/lo` | Insert, resize, reload ODP/PPTX, data sheet sync |

## Tests

- `core/table.py`: typed cells, escaping, invalid marker syntax, number formatting, column width
  normalisation, heatmap min/max and contrast, empty grid.
- `core/matrix.py`: fixed columns, missing size/group, split defaults and manual values, points
  outside the range.
- Layouts: cell rectangles, text boxes, borders, header/zebra fills, Harvey/check/sparkline
  primitives, quadrant lines and labels; structure independent of size.
- State: validation matrix (table with annotations rejected, matrix with sort rejected), round-trip,
  migration.
- Deck spec: build a table and a matrix; malformed marker reports the placeholder.
- `tests/lo`: insert, edit the data sheet, change table options, undo, resize, save/load ODP and
  PPTX, CSV export. Native table comparison is manual.
- Manual: look of the table in a corporate scheme, text alignment and wrapping in cells.

## Open questions

- Is `kind="table"` acceptable in the stored model, or does it make `ChartState` too broad? The
  alternative is a separate `TableState` with duplicated store/render paths. The ADR must decide.
- Merged cells, multi-line cell text and rich text are common; v1 supports none of them. Is a
  table without merges useful enough for the first release?
- Column widths: a width list in a dialog is clumsy. A grid editor (like the chart data sheet) would
  be better but is a second editor UI. Start with equal widths and a width field, learn from use.
- Heatmap ramp: scheme-derived or an explicit two-colour ramp? The scheme makes corporate design
  easy; an explicit ramp is more flexible.
- Sparkline data: inline in the cell versus a hidden range. Inline is self-contained but makes the
  data sheet noisy; a hidden range needs a second table. Start inline.
- Matrix axis end labels and quadrant labels are eight text fields; a compact dialog with two tabs
  may be needed.
- Should a matrix allow manual point positions (drag)? That is a chart-editing feature, not a data
  feature; defer.

## Out of scope

- A full spreadsheet-like table editor on the slide.
- Merged cells, images in cells, conditional formatting rules, pivot tables.
- A native Impress table or interoperability with existing Writer/Impress tables.
- Matrix annotations, dragging points, transposed orientation.
