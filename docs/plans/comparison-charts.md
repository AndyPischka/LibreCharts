# M24: Comparison and distribution charts

- Status: proposed
- Milestone: M24 (6.0)
- Builds on: M9 (scatter and butterfly, ADR 0018), M15 (floating bars, ADR 0025), M13/M16 (labels),
  M5 (sorting, ADR 0013)
- Decision: one ADR for the new chart kinds and their data sheets before implementation

## Goal

The existing kinds cover shares, changes over time and composition, but not the everyday comparison
questions: "before vs after", "actual vs target", "which few categories cause most of the effect",
"where do cases drop out of the funnel", and "how wide is the spread". M24 adds five focused kinds
instead of more options on the existing ones. Each reuses a layout idea that already exists.

## Scope

### Dumbbell / slope chart

- One row per category, two values per row: the start and the end point of a connector.
- The data sheet uses the paired-row convention of floating bars (`core/datasheet.ranged`): the
  first row of a pair is the start level, the second the end level; the pair's name is the series
  name but is not drawn as a legend unless the user asks for one.
- Horizontal by default (the bar-chart orientation), with a vertical variant. The `horizontal`
  option becomes valid for this kind too.
- Each point is a marker in its series colour; the connector is a line in the line colour. Labels at
  both ends are optional (start, end, difference), with the existing number format.
- Sorting by start, end or difference is possible through the existing sort mechanism; the category
  order is the data sheet order otherwise.
- Difference arrows between the two points are a natural fit. M24 may draw them with the existing
  annotation geometry, but the ADR can also defer arrows to M14 follow-up; the points and connector
  are the must-have.

### Bullet chart

- Horizontal KPI bars, one category per row. Fixed columns like scatter and Gantt:
  `Label | Actual | Target | Max`, with an optional `Qualitative max` column for a light band from
  0 to the maximum. The first row is the header.
- The actual value is a solid bar in the first palette colour, the target a short vertical marker in
  the line colour, and the scale runs from zero to `Max`. The value axis and gridlines are optional
  and follow the chart format.
- No categorical legend, no stacking, no negative values (a negative actual is drawn as zero and
  reported in the data sheet as invalid? Better: reject with a message in the data sheet).
- The bullet chart is a new `kind` but its data sheet is fixed-column, not the category/series grid.
  It gets a parser like `core/scatter.py`.

### Pareto chart

- Not a new kind. A column or bar chart gains `pareto: true`: exactly one series, sorted descending
  by value, with a cumulative percentage line on a right-hand axis from 0 to 100 %.
- The bars keep the existing column/bar layout options that make sense: axis, gridlines, number
  format, colours, patterns, but not stacking, 100 %, floating bars, error bars, line series or a
  secondary axis. Validation rejects the combinations.
- The cumulative line has markers at the category centres and labels with the running percentage
  (0-100 %); the right axis shows 0, 25, 50, 75, 100 or a 20 % step when the chart is narrow.
- The 80/20 line is a value line on the percentage axis, optional. The existing value line is a
  value-axis annotation; the Pareto layout can add a fixed 80 % helper line without a new
  annotation kind.
- Sorting: `pareto` implies descending and hides the sort switches. The data sheet order is the
  tie-breaker, like `sorting.py` does today.

### Funnel chart

- One series, one category per stage, drawn as centred horizontal bars whose width follows the value.
  The stage order is the data sheet order; sorting is disabled because a funnel is a sequence.
- Labels inside or right of each bar: value and, optionally, the conversion rate to the previous
  stage. The existing number format applies to the value; the conversion is a share label.
- No value axis by default; gridlines and an axis are optional like on a bar chart. No negative
  values; zero stages are allowed and draw as a minimum-width stub.
- No difference/CAGR arrows in v1. A conversion arrow between two stages is a later extension; the
  existing pick geometry has no funnel hit-test yet.

### Box plot

- One row per category, fixed columns:
  `Label | Min | Q1 | Median | Q3 | Max`, optionally followed by outlier values
  (`Outlier 1`, `Outlier 2`, ...). The first row is the header.
- The layout draws a box from Q1 to Q3, a median line, whiskers to Min/Max and outlier dots. The
  vertical orientation is the default; horizontal is a later option.
- The data sheet takes a five-number summary. Computing the summary from raw samples is out of
  scope: the user prepares it in Calc (or a later import feature).
- Axis, gridlines and number format follow the chart format. Difference arrows are not drawn in v1.

## Data model

- Extend `ChartKind` with `"dumbbell"`, `"bullet"`, `"funnel"` and `"boxplot"`.
- `ChartState.pareto: bool = False` for the column/bar option; validation as above.
- `horizontal` becomes valid for `dumbbell` too (and stays waterfall-only otherwise).
- New fixed-column parsers:
  - `core/bullet.py`: rows -> `BulletRow(label, actual, target, maximum, qualitative)`.
  - `core/boxplot.py`: rows -> `BoxRow(label, minimum, q1, median, q3, maximum, outliers)`.
- Dumbbell uses `core/datasheet.ranged`; funnel uses `core/datasheet.parse`.
- Schema version bump and `core/state_io.py` migration. New kinds have no old state; the parser
  rejects malformed fixed-column sheets with a message key, not an exception.
- `core/alttext.py` gets a `kind_*` key and a data description for each new kind.
- `core/options.py` gets the bullet/dumbbell/funnel switches that make sense; `SORTABLE` gains
  `dumbbell` and maybe `bullet`? A bullet chart is normally ordered by the data sheet; keep it out.
- `core/picking.py` gets hit-tests only where annotations are supported. At minimum value lines on
  bullet and difference arrows on dumbbell; the rest is documented as a follow-up.

## Approach

1. **One kind at a time, end to end.** Start with the dumbbell: model, parser, layout, renderer,
   insert command, sample data, alt text, CSV, deck spec, tests. Then bullet, Pareto, funnel, box.
   This keeps each change reviewable and avoids a large all-at-once schema diff.
2. **Reuse the layout primitives.** No new primitive types should be necessary except a marker with
   a different shape for the bullet target (a short `Line` works) and outlier `Marker`s. A box is
   a `Rect` with a `Line` for the median, whiskers are `Line`s.
3. **Data sheet UI.** The fixed-column sheets are edited in the same Calc window. The column headers
   are sample data, so the sheet explains itself; `lo/datasheet.py` needs no special date handling.
4. **Commands and menu.** New insert commands (`InsertChart?kind=dumbbell` etc.) in
   `extension/Addons.xcu`, the menu, the toolbar and the sidebar. Pareto is a switch in the column/
   bar context menu (`ChangeChart?pareto=true`), not an insert entry.
5. **Deck specification and CLI.** `core/deck.py` accepts the new kinds and `pareto`; `poe deck
   build` can create them from JSON. Add one sample to the documentation.
6. **Docs and translations.** New kind names, data sheet help, chart descriptions and UI strings in
   `core/messages.py` (English + German), then `uv run poe locales`. New icons in `extension/images`
   (16 and 26 px).

## Affected modules

| Module | Change |
|---|---|
| `core/model.py` | New kinds, `pareto`, validation, schema version |
| `core/state_io.py` | Migration; new kind state passes through |
| `core/datasheet.py` | Reuse `parse`/`ranged`; sample data for new kinds |
| `core/bullet.py`, `core/boxplot.py` | New fixed-column parsers and validation |
| `core/layout/dumbbell.py`, `bullet.py`, `pareto.py`, `funnel.py`, `boxplot.py` | New layouts |
| `core/layout/chart.py` | Dispatch the new kinds |
| `core/options.py` | Dumbbell orientation, Pareto switch, sort restrictions |
| `core/sorting.py` | Pareto ordering and source order tie-break |
| `core/picking.py`, `core/annotations.py` | Supported annotation kinds per new kind (minimal) |
| `core/alttext.py`, `core/csvexport.py` | Kind names, descriptions, CSV (generic where possible) |
| `core/deck.py`, `core/cli.py` | New kinds and `pareto` in specifications |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Insert entries and switches |
| `lo/chart.py`, `lo/commands.py`, `lo/datasheet.py` | Insert, redraw, sample data |
| `extension/Addons.xcu`, `extension/images/`, `extension/description/` | Entries, icons, release notes |
| `tests/lo` | Insert, edit, resize, reload each kind |

## Tests

- Parsers: valid rows, empty rows/columns, text in numeric cells, negative values (rejected or
  clamped with a message), missing target/max, box rows out of order (`min <= q1 <= median <= q3 <=
  max`), outliers.
- Layouts: geometry for known boxes, labels, axis, Pareto cumulative values and 80 % line, funnel
  widths and conversion labels, bullet target marker. Primitive structure constant across sizes
  (ADR 0007).
- State: validation rejects Pareto on a stacked/100 % chart, `pareto` with more than one series,
  funnel sorting, negative box values; migration and round-trip.
- Deck spec: build a deck with each new kind; a malformed fixed-column sheet reports the placeholder
  and message.
- `tests/lo`: insert each kind, edit the data sheet, undo, resize, save/load ODP and PPTX, CSV export.
- Manual look check for each kind (labels, line weights, colours).

## Open questions

- Dumbbell with more than two points per category (e.g. 2022, 2023, 2024): support `N` rows per
  category as a polyline, or keep pairs and use one chart per pair? Start with pairs.
- Bullet qualitative bands: fixed 33/66/100 %, data columns, or none? Start with none and a `Max`
  column; add bands when a real user asks.
- Pareto with multiple series: a separate mini-Pareto per series is usually wanted, not a stacked
  cumulative line. Keep one series per chart.
- Funnel conversion labels: relative to the first stage or the previous stage? Offer both as a
  format switch later; v1 shows both? Pick previous-stage in the ADR.
- Box plot from raw samples: belongs to a data import feature, not to the layout.
- Annotation support on the new kinds: which arrows are meaningful and testable? The ADR lists the
  matrix instead of promising "everywhere" again.

## Out of scope

- A general "chart from arbitrary table" importer (M28).
- Horizontal box plots, funnel conversion arrows, bullet qualitative bands.
- Statistical computations (quartiles, regression) beyond the five-number summary.
