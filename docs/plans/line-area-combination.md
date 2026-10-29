# Plan: M7 line, area and combination charts

Status: draft, not yet agreed (2026-10-29). Builds on M5 (variants) and M6 (value axis, format).

## Goal

- **Line charts**: one line per series over the categories, value labels at the points, the
  series name at the end of each line.
- **Area charts**: stacked areas, and 100 % areas (the M5 variant switch).
- **Combination charts**: on a column chart, single series are drawn as lines, optionally on a
  **secondary axis** right of the plot.

Non-goals: scatter charts with a numeric x axis (3.0, M9), smoothed lines, date axes.

## Approach

### State (`core/model.py`, `core/state_io.py`)

- `ChartKind` gets `"line"` and `"area"`. Line charts keep `grouping = "stacked"` without meaning
  (as waterfalls do); area charts use `grouping = "stacked"` and `percent` for 100 % areas.
- Combination: `ChartState.lines: tuple[int, ...]` (series indices drawn as lines) and
  `secondary: tuple[int, ...]` (subset of `lines` on the right axis). Only column charts may have
  them. Indices are data sheet rows, like annotation indices: a series row inserted above shifts
  them, a removed row leaves a dangling index that is ignored (same rule as `notes.drawable`).
- `Format.markers: bool = True` (M6 `Format`) for point markers on lines.
- Schema version 7; migration adds `lines: []`, `secondary: []`, `markers: true`. New chart kinds
  need the version bump too: older builds would otherwise report "malformed" instead of
  "saved by a newer LibreCharts".

### Primitives and rendering (`core/primitives.py`, `lo/render.py`)

- New `Polyline(points, series)` and `Polygon(points, series)`; points in chart coordinates.
  Rendered as `PolyLineShape` / `PolyPolygonShape` via the `PolyPolygon` property. One shape per
  line or area, so a series stays one selectable object.
- New `Marker(x, y, series)`, rendered as a small `EllipseShape` of fixed size.
- `Line` keeps its "bounding box" restriction; diagonal segments only occur in `Polyline`.
- `render.sync_geometry` (resize, ADR 0007) sets `PolyPolygon` for these shapes instead of
  position and size; the shape-type check gets the new types.
- To verify first with a spike in `tests/lo`: polyline coordinates inside a group, scaling on
  group resize, and the PPTX round trip (import may turn them into custom shapes, as it does
  with text boxes).

### Layout

- New `layout/line.py`: category slots as for columns, points at the slot centres, scale from
  `value_axis` (including zero, so the axis break from M4 can cut the empty range). An empty
  value splits a line: one `Polyline` per run of values, so the structure depends on the data
  only. Value labels above the points (below for negative values), the series name right of the
  last point (role `"series"`).
- New `layout/area.py`: cumulative sums per category, one `Polygon` per series between its lower
  and upper edge. Negative values count as empty (the shared rule from M5); empty values count
  as zero so the areas stay closed. 100 %: the M5 `shares` function first.
- Combination in `layout/column.py`: series in `lines` are left out of the stacking and drawn as
  `Polyline` + `Marker` over the column centres. With `secondary`, a second `nice_axis` over those
  series; the secondary scale is only readable with an axis, so it always draws an axis on the
  right (M6), even if the primary axis is off.

### Annotations

- Line charts: value lines (M6) and the axis break. Difference and CAGR arrows between two points
  of one series: see open question 3.
- Area charts: value lines only.
- Combination charts: arrows measure columns as today; line series cannot be picked.

### Commands and UI

- `InsertLineChart`, `InsertAreaChart`: menu, toolbar (new 26 px icons), sidebar (16 px). Sample
  data: two series over 2020..2025.
- Combination: a pick command `PickSeries?as=line` ("Show series as line" / "Datenreihe als
  Linie"): click a segment of the series (pick mode, ADR 0010), then
  `ChangeChart?line=<series>&on=true`. The context menu lists the line series with "Show as
  columns" and "Right axis" / "Linke Achse" switches.
- Status line: "Line chart" / "Liniendiagramm", "Area chart (100 %)", "Column chart with lines".

## Affected modules

`core/model.py`, `core/state_io.py`, `core/primitives.py`, new `core/layout/line.py`, new
`core/layout/area.py`, `core/layout/column.py`, `core/layout/chart.py`, `core/datasheet.py`
(samples), `core/annotations.py`, `core/picking.py`, `core/options.py`, `core/menu.py`,
`core/panel.py`, `core/messages.py`, `lo/render.py`, `lo/chart.py`, `lo/commands.py`,
`lo/pick.py`, `extension/entry.py`, `extension/Addons.xcu`, `extension/images/`.

## Tests

- `tests/core`: migration v6 -> v7; line points and labels, gaps split lines (structure per data,
  not size); stacked and 100 % areas, negatives ignored; combination: line series left out of
  stacks, secondary scale and right axis; dangling `lines` indices ignored; picking a series.
- `tests/lo/test_line.py`, `tests/lo/test_area.py`: insert, data sheet edit, resize (polylines
  follow the new size), undo, ODP and PPTX reload. `test_combination.py`: switch a series to a line
  and to the right axis, undo, reload.

## Docs

New ADR "Line, area and combination charts" (polyline primitives, per-series indices, why
`secondary` forces an axis); ARCHITECTURE.md (new layouts, primitives); glossary ("Line chart",
"Area chart", "Combination chart", "Secondary axis", "Marker"); CHANGELOG; ROADMAP; README.

## Open questions (recommendation first)

1. Point labels: at every point (recommended; off via a format switch later) or only at the
   last point.
2. Markers on by default (recommended) or off.
3. Difference and CAGR arrows between points of one series: in M7 (recommended: the arrow code
   only needs anchors; picking a point is the main work) or later.
4. Combination as a column chart with `lines` (recommended) or as a separate kind `"combo"`.
5. Line series stored by index (recommended, like annotations) or as a marker column in the data
   sheet (visible in Calc, but it would shift the category columns).
