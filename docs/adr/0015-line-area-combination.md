# 0015. Line, area and combination charts

- Status: accepted
- Date: 2026-10-29

## Context

M5 and M6 gave column, bar, waterfall and Mekko charts their variants, axes, labels and number
formats. Two chart types were still missing: line charts (trends over time) and area charts (a
stacked volume over time), and there was no way to show a single series of a column chart as a line
next to the columns — the usual way to put a value with another unit (a margin, a headcount) on
the same slide, which needs its own axis. All of it must survive data edits, undo, copies, resize
and ODP/PPTX files like the rest of the chart state.

## Decision

Agreed with the maintainer in `docs/plans/line-area-combination.md` (recommended answers to its
open questions):

- **Chart kinds**: `ChartKind` gains `"line"` and `"area"`. A line chart keeps
  `grouping = "stacked"` without meaning (like a waterfall); an area chart is always stacked and
  uses the existing `percent` field for its 100 % variant. Area charts therefore use the M5 variant
  switch; line charts have no variant.
- **Format**: `Format.markers: bool = True` switches the point markers of a line series. New line
  charts show markers, labels at every point and the series names right of the last point
  (`default_format`).
- **Combination state**: `ChartState.lines: tuple[int, ...]` (series drawn as lines) and
  `ChartState.secondary: tuple[int, ...]` (`secondary ⊆ lines`, on the right axis). Only column
  charts may have them; a 100 % chart cannot. Indices are data sheet rows like annotation indices:
  a dangling index is kept and ignored, so undoing a data edit brings the line back.
- **Schema version 7**: `_v6_to_v7` adds `lines: []`, `secondary: []` and `format.markers: true`.
  The kind values alone would also need the bump, so that an older build reports "saved by a newer
  LibreCharts" instead of "malformed".
- **Primitives**: `Polyline(points, series)`, `Polygon(points, series)` and `Marker(x, y, series)`.
  A line or area is one shape (`PolyLineShape`, `PolyPolygonShape`) so it stays one selectable
  object; a marker is a fixed-size `EllipseShape` (`MARKER_SIZE`), so resizing does not blow it up.
  `Line` keeps its restriction to horizontal, vertical and 45° lines; diagonal segments only occur
  in a `Polyline`.
- **Layout**: new `layout/line.py` (points at the slot centres, an empty value splits the line into
  one polyline per run, a label at every point above it, below for negative values) and
  `layout/area.py` (one polygon per series between its cumulative edges, 100 % via the M5 shares).
  In an area chart a negative value counts as empty and an empty value as zero, so the areas stay
  closed. `layout/column.py` grows the combination: line series are left out of stacking,
  clustering, totals and picking, share the primary scale unless they are on `secondary`, and a
  secondary axis is always drawn (M6), even when the value axis is off.
- **Annotations**: a line chart supports difference arrows, CAGR arrows, an axis break and value
  lines; an arrow may measure one series (`series=<index>`), anchored at its points. An area chart
  supports value lines only. On a combination chart an arrow can measure a line series at its
  point; its label and lanes work as on columns.
- **Commands and UI**: `InsertLineChart` and `InsertAreaChart` in the menu, toolbar, sidebar and
  `entry.py`. The context menu of a column chart gets "Series as lines" with one entry per series
  (`ChangeChart?line=<index>&on=true|false`) and, for a line series, its primary/secondary switch
  (`ChangeChart?secondary=<index>&on=true|false`). The command carries exactly one option plus
  `on`, so each click is one undo step. The sidebar status names the new kinds and a combination
  chart.

## Alternatives considered

- **A separate chart kind `"combo"`**: a combination is a column chart with a display option; a new
  kind would duplicate the whole column layout and break the variant switches.
- **Line series as a marker column in the data sheet**: visible in Calc, but it would shift the
  category columns and change how the data is read; an index list is the same rule as annotations.
- **A pick command "show series as line"**: picking a segment would need a new pick session kind
  and a new undo path for a toggle that the context menu can offer directly, one entry per series
  with the current state visible.
- **Markers off by default**: a line chart without markers hides the actual years; think-cell and
  empower charts show them.
- **Labels only at the last point**: a reader cannot tell the intermediate values; every point is
  labelled, and a format switch can hide the markers later.
- **Scaling a marker with the group**: a resize would produce huge dots; markers stay
  `MARKER_SIZE` and `sync_geometry` leaves their size alone.
- **Difference arrows on area charts**: an area has no single value to anchor an arrow to; the
  value line is the annotation that makes sense there.

## Consequences

- Schema 7 documents cannot be read by older builds; their shapes still display.
- Line and area charts follow the layout invariants: the primitive structure depends on the data
  and the format only, never on the size (ADR 0007). `sync_geometry` moves poly shapes through
  `PolyPolygon` and reuses the existing children, so a resize stays one native undo step.
- `percent=true` clears `lines` and `secondary` (a 100 % chart has no line series); switching to
  clustered keeps them. Both rules live in `core/options.py` and are tested there.
- `variants()` now emits `ChangeChart?grouping=stacked` without `percent=false`, because
  `options.changed` accepts exactly one option per call; `_grouping` always leaves the 100 %
  variant. The old pair of arguments was silently rejected by the command, untested in `tests/lo`.
- The line and area layouts share the top band, lanes and axis code with the column layout in
  `layout/common.py`; a later chart type reuses them instead of copying them.
