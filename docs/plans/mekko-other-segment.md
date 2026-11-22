# M34: Mekko — combine small segments into "Other"

- Status: draft, to be agreed
- Milestone: M34
- Complexity: M (data transformation + layout, no new chart type)
- Builds on: M3 (Mekko, ADR 0009/0012), M14 (annotations on Mekko), M16 (rounding, decluttering)

## Goal

think-cell can bundle small Mekko segments into one *Other* segment to reduce noise. LibreCharts
shows every series row. Add a per-chart option that combines series below a threshold into a
single *Other* series per column, displayed in a neutral colour, with its share labelled like any
other segment.

## Approach

### Semantics

- Option on the chart state: `other_threshold: float | None` (percent, e.g. 5 = combine series
  whose share is below 5 % **in every column**), plus the neutral colour from the scheme.
  `None` = off (default), so existing charts are unchanged.
- The threshold is evaluated on **shares**, per the chart's variant: percent Mekko uses the share
  within each column; units Mekko uses the share of the column sum as well (decide in review:
  share of column vs. share of grand total — proposal: column, consistent with the percent view).
- A series is combined only if it is below the threshold in **all** columns; otherwise it stays
  (otherwise a series could vanish exactly where it matters). The *Other* series is appended as
  the last series, sums per column, and gets a translated label *Other* / *Sonstige*.
- Transformation happens in `core/` as a pure function `with_other(data, threshold) -> ChartData`
  applied before layout — sorting (M5), consistent rounding (M16: shares still sum to exactly
  100 %, including *Other*) and decluttering keep working on the transformed data.
- The data sheet is **not** modified: this is a display option like the category sort (ADR 0013).
  The chart's alternative text and CSV export state whether they describe the raw or the displayed
  data (proposal: raw data for CSV export, displayed data for alt text — matches "what you see").

### Interaction with annotations and labels

- Difference/CAGR arrows anchored to a series that gets combined: keep the annotation but mark it
  unresolvable (hide, like the category-gap behaviour when sorting separates its categories),
  restore it when the threshold is lowered again. Arrows to *Other* itself are allowed (it is a
  normal series for picking).
- Series colour overrides (M8) follow the displayed series; *Other* always uses the scheme's
  neutral colour, not a palette slot.

### UI

- Context menu + sidebar *Format* section: *Combine small segments...* opens the number-format-like
  dialog asking for the threshold (0 = off). One undo step. Deck-build spec field
  `other_threshold`.

## Affected modules

| Area | Modules |
|---|---|
| Transformation | new `core/other.py` (pure function), called from `core/layout/mekko.py` entry |
| Option/state | `core/model.py`, `core/options.py`, `core/state_io.py` (optional field, no break) |
| UI | `lo/commands.py`, `lo/formatdialog.py` (threshold dialog), `core/panel.py`, `core/messages.py`, `core/locales/*` |
| Annotations | `core/annotations.py` (unresolvable-anchor handling, mirrors category gap) |
| Export/alt text | `core/csvexport.py`, `core/alttext.py` (raw vs. displayed decision) |

ADR: small one only if the annotation-hiding rule diverges from ADR 0013's display-only principle;
otherwise extend the Mekko ADRs by reference in the plan review notes.

## Test strategy

- `core/`: threshold boundaries (exactly at threshold stays), series below in all columns vs. one
  column, *Other* position and sum, shares still round to 100 % (M16), units and percent variants,
  sorting applied after combining, no *Other* when nothing qualifies.
- Layout invariants: same primitive structure across sizes for fixed data+threshold.
- `tests/lo/`: set threshold on a real Mekko, undo in one step, annotation on a combined series
  hides and returns, save/reload ODP and PPTX.
- `uv run poe check`, `uv run poe test-lo`; CHANGELOG, feature list, README option list.

## Open questions

- Threshold on share of column vs. grand total (proposal: column).
- Should *Other* be expandable (click to show its parts)? Proposal: no interaction in v1; lowering
  the threshold is the way.
- Pie charts have the same need — implement the pure function chart-kind-agnostic but wire only
  Mekko now? Proposal: yes, function generic, UI wiring Mekko only; pie follows as S later.

## Out of scope

- Combining *columns* (categories) instead of series, automatic threshold suggestions, drill-down.
