# M35: Chart variants — gauge/pie-of-pie, scatter partitions, candlestick

- Status: draft, to be agreed; three independent work packages, each shippable on its own
- Milestone: M35 (order within the milestone by user feedback)
- Complexity: M each
- Builds on: M9 (pie, scatter), M15 (floating bars), M23 (log axis, manual axes)

## Goal

Close the remaining think-cell chart-variant gaps from
[docs/thinkcell-feature-list.md](../thinkcell-feature-list.md):

1. **Pie family:** gauge charts, break-out slices, concentric doughnuts (pie-of-pie optional, see
   open questions).
2. **Scatter partitions:** shaded/coloured background regions for scenarios and heat maps.
3. **Candlestick / football-field charts** as line-chart variants.

Each package follows the same pattern: extend the chart state with optional fields (old files read
unchanged), keep layout a pure function of data+size, one undo step per UI action, tests in
`core/` plus `tests/lo/`.

## Package 1: Pie family

- **Gauge:** a doughnut option `gauge: bool` draws a half (or 270°) doughnut with the total or a
  needle-style marker; data is one category with two series (value, remainder). Keep it an option
  of the existing pie layout (`core/layout/pie.py`), not a new chart kind.
- **Break-out slices:** per-segment offset (state: set of `(category, series)` keys or a per-series
  flag) moves a segment radially outwards by a fixed fraction of the radius; picking and labels
  follow the moved segment; annotation anchors use the moved centre.
- **Concentric doughnuts:** option `concentric: bool` draws one ring per category instead of
  separate pies, sharing the centre; shares labelled per ring. Check primitive-structure invariant:
  ring count depends on data only.
- Pie-of-pie (a second pie detailing one segment) is the most complex of the family; only start it
  if users ask — it is close to M34's *Other* transformation plus a second plot.

## Package 2: Scatter partitions

- State: list of rectangular regions in **data coordinates** (`x1, y1, x2, y2`, fill colour,
  optional label), edited in a small dialog or as extra data-sheet columns (decide in review;
  proposal: dialog + state, like annotations, because regions are decoration not data).
- Layout (`core/layout/scatter.py`): regions become `Rect` primitives behind the points, clipped to
  the plot; a region label sits in its corner. Regions use the same scale (incl. log axis M23) and
  the same axis mapping as points; no hit-testing needed in v1 (edit via dialog list).
- Heat-map use case: regular grids of regions can be generated from the dialog (rows×columns),
  no separate chart type.

## Package 3: Candlestick / football field

- Reuse M15 floating bars: a candlestick is a floating bar (open/close) plus a whisker (low/high);
  the data sheet takes four value rows per category (Open, High, Low, Close) — parse in a new
  `core/candlestick.py`, layout as narrow floating bars + `Line` whiskers, up/down colours from the
  scheme.
- Football field: horizontal floating bars (already possible via M15 + bar chart) with a value
  line; if that is sufficient, document the recipe in the README instead of adding a chart kind.
- Candlestick is a new `kind` only if the four-row data sheet cannot be expressed as an option of
  the floating-bar column chart — prefer the option route.

## Affected modules

| Package | Modules |
|---|---|
| Pie family | `core/layout/pie.py`, `core/model.py` (options), `core/options.py`, `lo/commands.py`, `core/panel.py`, `core/messages.py`, `core/locales/*` |
| Scatter partitions | `core/model.py` (region state), `core/layout/scatter.py`, `lo/formatdialog.py` or new dialog, `core/messages.py`, `core/locales/*` |
| Candlestick | `core/candlestick.py` (parse), `core/layout/column.py`/`bar.py` (floating bars + whisker), `core/model.py`, `core/messages.py` |

ADRs: one short ADR per package if a new state concept appears (regions, per-segment offsets);
gauge/concentric as pie options need none beyond a note in ADR 0018's follow-up.

## Test strategy

- `core/`: geometry of gauge angles, break-out offsets (labels/annotations follow), concentric
  rings; partitions in linear and log scales, clipped at plot edges; candlestick OHLC validation
  (low ≤ open/close ≤ high) and up/down colouring.
- Layout invariants for every variant: same primitive structure across sizes.
- `tests/lo/`: insert and toggle each variant, one undo step, save/reload ODP/PPTX, deck-build
  spec fields.
- `uv run poe check`, `uv run poe test-lo`; CHANGELOG + feature list per shipped package.

## Open questions

- Pie-of-pie: defer until requested, or include in M35? Proposal: defer (largest piece, M34 covers
  most of the need).
- Scatter partitions as annotation-like state (proposal) vs. data-sheet columns.
- Candlestick: option on floating bars (proposal) vs. new chart kind.
- Gauge with needle: real needle shape or just the filled arc in v1? Proposal: filled arc first.

## Out of scope

- Interactive region editing by dragging, 3D pie effects, stock-market data feeds, true box-plots
  beyond M24.
