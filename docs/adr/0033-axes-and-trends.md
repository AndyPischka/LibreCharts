# 0033. Manual axes, logarithmic scale and trendlines

- Status: accepted
- Date: 2026-11-20

## Context

The automatic nice axis is a good default but a deck needs fixed ranges, titles, a log scale and a
trend. All of them change the geometry of every layout, so they need one shared axis model.

## Decision

- **`Format` holds the manual axis**: `axis_min`, `axis_max`, `axis_step`, `axis_scale` (linear or
  log), `axis_title`, `category_axis_title`. A missing bound is derived from the automatic axis.
- **`Axis` knows its scale** and maps values with `fraction()`. Linear layouts keep their formula;
  line and scatter use the fraction, which makes log support a one-line branch. A log axis rejects
  non-positive data.
- **Truncated baselines stay visible**: a manual minimum above zero draws a cut mark at the axis
  foot. The dialog asks once; the stored minimum is the confirmation.
- **Titles reserve a band** (`AXIS_TITLE_BAND`); `Text.rotation` rotates the value title on
  vertical axes. The renderer writes Draw's `TextRotation`.
- **Trendlines are data, not format**: `Trend(series, kind, forecast, show_r2, show_equation)` in
  `ChartState.trends`, at most one per series. `core/trend.py` fits least squares and log-y; the
  layouts draw a solid line over the data and a dashed forecast, plus an R² label.
- Schema 18 stores the fields; old charts get automatic axes and no trends.

## Consequences

A trendline follows sorting and data edits automatically. The confidence band is deliberately left
for a follow-up: it needs a transparent filled primitive.
