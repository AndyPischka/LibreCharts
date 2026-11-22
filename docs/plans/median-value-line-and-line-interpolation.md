# M32: Quick wins — median value lines and line interpolation

- Status: draft, to be agreed
- Milestone: M32 (first open items of [docs/thinkcell-feature-list.md](../thinkcell-feature-list.md))
- Complexity: S + S (one round, two independent features)
- Builds on: M6 (value lines, ADR 0014), M7 (line charts, ADR 0015)

## Goal

Two small think-cell features that extend existing code instead of adding subsystems:

1. **Median value line.** The value-line dialog currently offers *Average* or a manual value.
   think-cell also offers a median. The median is a third choice that marks the median of the
   column sums (same data the average uses).
2. **Linear interpolation of missing values in line charts.** Today an empty value splits a series
   into several lines. think-cell can interpolate linearly across gaps. A per-chart switch chooses
   between *gap* (current behaviour, stays the default) and *interpolate*.

## Approach

### Median value line

- `core/value_line.py`: `average()` gets a sibling `median()` (same column sums; even count takes
  the mean of the two middle values). `average_for(state)` generalises to `statistic_for(state,
  mode)` so waterfall levels and scatter y values work as for the average.
- `core/model.py`: the annotation needs to remember *which* statistic it shows. Today
  `value is None` means average. Add a small enum on `Annotation` (e.g. `value_line_mode:
  "average" | "median" | None`); `None` keeps today's meaning, so every existing chart state
  reads unchanged. No schema bump needed if the field is optional and defaults to average —
  decide against `state_io.py` conventions.
- `core/annotations.py`, `core/layout/*`: `value_line.resolved(annotation, data)` dispatches on
  the mode; labels use a new message `menu_value_line_median` beside `menu_value_line_average`.
- `lo/formatdialog.py`: third radio *Median* in `_build_value_line`; `ask_value_line` returns the
  mode together with the value.
- Messages: `value_line_median` (dialog) and `menu_value_line_median` (annotation list), English +
  German in `core/messages.py`, then `uv run poe locales`.

### Line interpolation

- `core/model.py`: per-chart option `interpolate: bool` on the chart state (like `sort`, `lines`),
  default `False`. Optional field → old states read unchanged.
- `core/layout/line.py`: where the layout splits a series at `None` values, interpolation mode
  instead fills each gap linearly between the neighbouring known points and draws one continuous
  polyline. Points that were empty in the data get **no marker and no value label** (think-cell
  behaviour: the line bridges the gap, it does not invent data labels). Leading/trailing gaps are
  never extrapolated. Trendlines (M23) and error bars keep using real data only.
- Invariant check: the primitive structure must not depend on size — interpolation changes only
  coordinates, not the number of primitives, for a given data set. Document this in the module
  docstring.
- UI: *Interpolate missing values* toggle in the line chart's context menu *Format* section and the
  sidebar, one undo step; messages English + German, then `poe locales`.
- Deck build: `interpolate` becomes a spec field like `sort`/`lines` (README automation section).

## Affected modules

| Feature | Modules |
|---|---|
| Median | `core/value_line.py`, `core/model.py` (annotation mode), `core/annotations.py`, `lo/formatdialog.py`, `core/messages.py`, `core/locales/*` |
| Interpolation | `core/layout/line.py`, `core/model.py` (option), `core/options.py`, `core/panel.py`, `lo/commands.py` (toggle), `core/messages.py`, `core/locales/*`, `core/deck.py` (spec field) |

No new modules, no new ADR expected (both extend ADR 0014 / ADR 0015 mechanisms).

## Test strategy

- `core/`: median of odd/even/empty column sums, negative values, waterfall levels and scatter y;
  `resolved()` with explicit value still wins over any statistic.
- `core/`: interpolation fills single and multi-point gaps, no extrapolation at the ends, no
  markers/labels on interpolated points, gap mode unchanged; layout invariants (same primitive
  structure across sizes) for both modes.
- `tests/lo/`: toggle interpolation and add a median line on a real line chart; one undo step each;
  dialog logic tested in `core/` (dialogs are not drivable headless, see AGENTS.md).
- State round-trip: save/reload ODP and PPTX keeps mode and option; old files open unchanged.
- `uv run poe check`, `uv run poe test-lo`; update CHANGELOG and the feature list.

## Open questions

- Median of *column sums* (consistent with the average) or of *all values*? Proposal: column sums,
  and say so in the dialog tooltip — matches think-cell's "average" precedent in LibreCharts.
- Should the median line be available on Gantt (date lines) too? Proposal: no, date lines stay
  manual/average as today.
- Interpolated points: completely invisible, or a hollow marker to signal "no data"? Proposal:
  invisible in v1; a marker style can follow if users ask.

## Out of scope

- Other statistics (min, max, percentile) and net lines between series.
- Interpolation for area charts or combination charts' line series (follow-up if wanted).
- Extrapolation / forecasting (covered by M23 trendlines).
