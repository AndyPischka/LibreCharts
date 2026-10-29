# 0018. Pie, scatter and butterfly charts

- Status: accepted
- Date: 2026-10-29

## Context

M9 adds three chart types that think-cell and empower offer and LibreCharts lacked: pie and
doughnut charts, scatter and bubble charts, and butterfly (mirrored bar) charts. They must use the
existing pipeline (Calc data sheet, `ChartState`, pure layout, native shapes, format, colour
schemes, resize, undo, ODP/PPTX) without a second code path in the renderer.

## Decision

Taken from the M9 plan (removed after implementation), with the recommended answers to its open
questions:

- **Chart kinds**: `ChartKind` gets `"pie"`, `"scatter"` and `"butterfly"`; `grouping` stays
  `"stacked"` without meaning (as for line and waterfall charts). `ChartState.doughnut` (schema 9,
  migration adds `false`) turns a pie into a doughnut; the pie/doughnut switch is an option variant
  (`ChangeChart?doughnut=...`) like stacked/clustered.
- **Pie data**: the column chart's data sheet. Every category column is one pie, every series row
  one segment, so a stacked column chart's data shows as pies and every series keeps its colour
  across the pies. Negative and empty values count as empty (`core/percent.py`). One pie per
  category, not always a single one.
- **Segments are `Polygon`s** (`core/geometry.py: sector`), one code path for pie, doughnut and the
  Harvey balls of M12. The point count depends only on the sweep (one point per degree), never on
  the size (ADR 0007), so resize keeps the structure. Segments run clockwise from 12 o'clock in
  series order. A share goes inside its segment from 20 degrees upwards, else outside at 1.15 times
  the radius; the decision follows the data. A doughnut has a hole of half the radius with the sum.
  Sorting segments by size is not part of M9.
- **Series names on a pie** ("labels" in the format) are a legend column right of the last pie;
  "legend" is the usual legend band above. A pie has no axis and no gridlines.
- **Scatter data sheet** (`core/scatter.py`): one row per point, columns by position (label, x, y,
  size, group); the header row only names them. Rows without a numeric x or y are skipped. A
  positive size makes a point a bubble, so bubble charts need no extra kind; sizes of zero or less
  count as empty. A group (text) gives its points a colour and a legend entry, groups are numbered by
  first appearance and `ChartState.colors` indexes them. This fixed-column pattern is what the Gantt
  data sheet of M10 follows.
- **Scatter layout**: both axes are always drawn and do not include zero (`nice_axis(...,
  include_zero=False)`), so there is no axis switch, only gridlines. Point labels sit right of the
  point without collision avoidance. A value line (horizontal, y level; default the mean of y) is the
  only annotation; it extends the y axis if it lies outside the data.
- **`Bubble` primitive**: a circle whose diameter is layout output (unlike the fixed-size `Marker`),
  filled with 30 % transparency. The largest diameter is 12 % of the shorter plot side, areas are
  proportional to the sizes. The renderer treats it as an `EllipseShape` like a marker, so
  `sync_geometry` moves and resizes it on a resize. Bubbles are drawn largest first.
- **Butterfly**: the column chart's data sheet; the first series grows left, the second right from
  a central band with the category names, both on one scale (the larger maximum). Further series are
  ignored, and the sidebar status says so. Sorting (M5) applies, keyed by the first series (the
  layout is sorted as if clustered). Value axis (ticks under both halves) and gridlines are
  optional. The chart joins same-scale groups of horizontal charts (bar charts, ADR 0017).
  Negative and empty values draw no bar. No annotations in M9.
- **UI**: `InsertPieChart`, `InsertScatterChart` and `InsertButterflyChart` in the menu, toolbar and
  sidebar with 16 px and 26 px icons; the status line names "Pie chart", "Doughnut chart", "Scatter
  chart", "Bubble chart" and "Butterfly chart" (also in German).

## Alternatives considered

- **Native `EllipseShape` sections for pie segments** (`CircleKind.SECTION`): nicer to edit by hand,
  but there is no ring shape for doughnuts and the resize and Harvey-ball code would need a second
  path.
- **Collision avoidance for scatter labels**: left for later; the labels stay readable for the
  expected point counts and the layout stays simple and deterministic.
- **Stacking further butterfly series per side**: needs a way to say "left" or "right" per series
  in the data sheet; ignoring the rest is predictable.
- **A separate kind for bubble charts**: the size column already decides it per point.

## Consequences

- Charts saved by older versions migrate with `doughnut: false`; charts of the new kinds need schema
  9 and an older LibreCharts rejects them with its "saved by a newer LibreCharts" message.
- PPTX import turns polygons and ellipses into custom shapes: the integration tests check the
  shape types for ODP only and the texts for both formats.
- Pies with many series and tiny segments crowd their outside labels; sorting segments (M15) or label
  placement (M13) will address that.
