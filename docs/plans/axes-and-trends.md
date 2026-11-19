# M23: Axes, trendlines and forecasts

- Status: proposed
- Milestone: M23 (6.0)
- Builds on: M6 (axis, gridlines, number format, ADR 0014), M7 (line and combination charts), M14
  (axis break), M15 (error bars)
- Decision: new ADR before implementation (manual axes, logarithmic scale, trendline state)

## Goal

The automatic "nice" axis is a good default, but a deck often needs a fixed range to make two
slides comparable, a tick interval that matches the story, an axis title, or a trendline that shows
where the data is going. Today `core/scale.py` only computes `nice_axis()` and every layout derives
its geometry from a linear `Axis`; there is no manual limit, no title and no regression.

## Scope

### Manual value axis

- `axis_min`, `axis_max` and `axis_step`, each optional. Empty means automatic, as today.
- At least two of the three produce a valid axis; a missing bound is rounded outwards to the step,
  and a missing step uses the automatic nice step.
- For chart kinds that need a baseline (column, bar, area, waterfall, Mekko, butterfly), a manual
  minimum above zero is allowed only after an explicit confirmation in the dialog ("the bars are cut;
  readers may misread the chart"). The stored state is just `axis_min > 0`; reopening the deck does
  not prompt again. The layout draws bars and areas from the plot bottom and puts a cut mark at the
  axis foot, so the truncation stays visible after the dialog is gone.
- Line and scatter charts may start above zero without a confirmation; a truncated axis is normal
  there.
- The primary axis only. The secondary axis of a combination chart stays automatic in v1; its
  manual fields are a follow-up because the two axes interact.
- Axis break (M14) still works: the manual range is the unfolded axis, the break removes a range
  inside it, and a break outside the manual limits is rejected in the axis dialog.
- Works for every value axis: column, bar, line, area, Mekko, scatter, butterfly, Pareto (M24) and
  the value axis of a bullet chart.

### Axis titles

- A value-axis title and a category-axis title, each optional, at most 80 characters.
- The value title is rotated 90° on column, line, area, Mekko and scatter charts and horizontal on
  bar charts. This needs a `rotation` field on `core/primitives.Text`; the renderer sets
  `TextRotation`.
- The layout reserves a band for a title, so the plot does not overlap it. Rotated text has no
  measurement in `core/`; the band is a fixed height/width and the text is centred, clipped by the
  renderer if it is longer.
- Titles are part of `Format`, so *Copy chart format* copies them. A title that names one chart's
  unit is usually not wanted on another; the dialog offers to clear it when copying? Keep it simple:
  copy it, and document the behaviour.

### Logarithmic axis

- `axis_scale: "linear" | "log"` on the primary value axis. Only line and scatter charts in v1:
  column, bar, area, waterfall and Mekko need a zero baseline that a log axis cannot show.
- Zero and negative values make a log axis invalid; the dialog reports the offending series and
  refuses the switch. A log axis with an axis break is not offered.
- `Axis` learns a `fraction(value)` method (0 at the minimum, 1 at the maximum) and `ticks()` branches
  for a log scale (powers of ten, with 1-2-5 minor ticks inside a decade). Layouts that support log
  replace their linear formulas with `fraction`, so the geometry stays a pure function of the axis.
- Number labels use the existing format; a magnitude suffix can make `1 000 000` a `1 Mio.`.
- Minor gridlines: optional, maybe not in v1. The axis line and major ticks are required.

### Trendlines and forecasts

- One trendline per series: `linear` or `exponential` (a straight line in log-y space). `exponential`
  requires positive values.
- A trendline is computed from the evaluated values, not from formulas. Empty cells are skipped.
- Optional `forecast` in categories or x units: the line continues dashed beyond the last actual
  point. Line and scatter charts only; a column chart can show a trendline over its category centres
  but no forecast extension in v1.
- Optional R² label near the line end, formatted with the chart's language and decimal separator.
  The equation itself (`y = ...`) is optional; a short label is often better on a slide.
- Optional confidence band: a light band around the forecast, computed from the residual standard
  error. It needs a transparent filled primitive; `Polygon` has no transparency today. Add a
  `transparency` field or a `Band` primitive, or defer the band to a follow-up. M23 ships the line
  and the forecast; the band is a stretch goal.
- Trendlines do not apply to stacked or 100 % charts (a trend of a stack is rarely meaningful) and
  not to pie, Gantt or butterfly charts. The context menu offers them only where they apply.

## Data model

- `Format` gains `axis_min: float | None`, `axis_max: float | None`, `axis_step: float | None`,
  `axis_scale: Literal["linear", "log"] = "linear"`, `axis_title: str = ""` and
  `category_axis_title: str = ""`. All are finite, the step positive; min < max; titles at most 80
  characters.
- New `Trend` dataclass: `series: int`, `kind: Literal["linear", "exponential"]`,
  `forecast: int = 0`, `show_r2: bool = True`, `show_equation: bool = False`. `ChartState.trends:
  tuple[Trend, ...]`, at most one per series.
- `Text` gains `rotation: int = 0` (degrees, clockwise); only 0 and 90 are used by M23.
- Schema version bump and a migration in `core/state_io.py`: old charts get automatic axes, no
  titles and no trendlines. A chart with `axis_scale="log"` and non-positive data is rejected on
  load with `StateError` (or reset to linear with a warning, decide in the ADR).

## Approach

1. **Axis math first.** Extend `core/scale.py` with `manual_axis(low, high, step)` and an `Axis`
   that knows its scale. Keep `nice_axis()` as the automatic default and make the manual function
   reuse the same rounding rules.
2. **One way to build an axis.** `core/layout/common.value_axis` receives the `Format` and applies
   manual limits; the layout-specific secondary axis (`layout/column._secondary_axis`) stays
   automatic. For baseline charts the dialog asks before it accepts a minimum above zero; the model
   allows it because the confirmed case is valid.
3. **Geometry.** Add `Axis.fraction(value)` and replace the `(value - min) / span` /
   `length_per_unit` formulas in the layouts that support log. For linear axes `fraction` is the old
   formula, so the output is unchanged. The resize invariant (ADR 0007) still holds: the primitive
   structure depends on data, not on size.
4. **Titles and rotation.** Add the text band to the plot-box computation of each layout, and the
   rotation field to `Text` and `lo/render.py`. The renderer already sets text properties per shape.
5. **Trendlines.** New `core/trend.py`: least-squares fit, prediction, R², exponential fit via
   log-y, and a shared `draw_trend(...)` helper for line/scatter/column layouts. The helper returns
   a dashed `Polyline` and a `Text` label, so the renderer needs no new shape type.
6. **Commands and dialog.** `ChangeFormat?axis_min=...` etc. for simple switches; a modal
   *Axes...* dialog (`lo/formatdialog.py` or a new `lo/axisdialog2.py`) for limits, step, titles and
   log. `AddTrendline?series=...&kind=...` opens the trendline dialog; removing is a context-menu
   entry. One undo step per change.
7. **Alt text.** Axis titles and a trendline sentence are added to the description; the chart data
   itself stays the main content.

## Affected modules

| Module | Change |
|---|---|
| `core/model.py` | `Format` fields, `Trend`, validation |
| `core/state_io.py` | Schema bump and migration |
| `core/scale.py` | Manual and log axes, `fraction`, ticks |
| `core/axis_break.py` | Manual limits and break validation |
| `core/trend.py` | New: fits, predictions, R², trend primitives |
| `core/layout/common.py` | Manual axis, titles, log fractions |
| `core/layout/column.py`, `bar.py`, `line.py`, `area.py`, `mekko.py`, `scatter.py`, `butterfly.py` | Axis titles, manual axis, log where supported |
| `core/layout/line.py`, `scatter.py`, `column.py` | Trendline drawing, forecast band |
| `core/format.py` | Parse and validate the new format fields |
| `core/primitives.py` | `Text.rotation`, optional band transparency |
| `core/alttext.py` | Titles and trendline description |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Axis/trendline entries |
| `lo/formatdialog.py`, `lo/axisdialog.py` | Axis and trendline dialogs |
| `lo/render.py` | Text rotation, optional band transparency |
| `lo/commands.py`, `lo/contextmenu.py`, `lo/sidebar.py` | Commands and UI |
| `extension/Addons.xcu`, `extension/images/` | Entries and icons |

## Tests

- `tests/core/test_scale.py`: manual min/max/step, rounding, log ticks and fractions, log
  zero/negative rejection, `nice_axis` unchanged.
- Layout tests: manual axis output identical for all sizes; a confirmed cut baseline and its marker;
  axis titles reserve space; log geometry
  on line/scatter; break inside/outside manual limits; trendline polyline and R² label.
- `tests/core/test_model.py` + `test_state_io.py`: validation, migration, malformed trends.
- `tests/core/test_trend.py`: exact fits, noise, exponential, R², empty cells, forecast count.
- `tests/lo`: axis dialog values (logic tested in core; the dialog is manual), trendline add/remove
  undo, reload ODP/PPTX, resize after a title is set.
- Visual check by hand: rotated title, log axis, trendline with forecast.

## Open questions

- Manual limits on the secondary axis: same dialog with a tab, or a separate `Format` object per
  axis? The former is more UI work, the latter a schema change. Start with primary only.
- How is a truncated baseline drawn: reuse the axis-break mark, a small zigzag at the axis foot, or
  only the axis title? The confirmation must remain visible after the dialog closes.
- Is the confirmation remembered per chart (the stored minimum itself) or asked again when the dialog
  changes the minimum? The plan stores only the minimum; the dialog asks on each new value above
  zero.
- Log axis: should a column chart with a positive baseline be allowed (bars from a floor, not zero)?
  Standard tools allow it; it is confusing. Keep it out of v1.
- Confidence band: add transparency to `Polygon`, add a `Band` primitive, or skip. Decide after the
  line and forecast work.
- Trendline on a grouped bar chart: one line per series would clutter. Offer only for list-like
  charts (line, scatter, single-series column) in v1.
- Equation text and R² in the chart language: use `format_value` or a separate formatter? R² is not
  a chart value and should not get a magnitude suffix.

## Out of scope

- Category-axis tick intervals and date-axis formatting (Gantt has its own time scale).
- Error bands, moving averages and polynomial trendlines.
- Manual axis limits for pie, Gantt or the secondary axis.
- Axis breaks on a logarithmic axis.
