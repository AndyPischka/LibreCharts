# 0025. Range and waterfall variants: floating bars, error bars, stacked/horizontal waterfalls, pie segment sort

- Status: accepted
- Date: 2026-11-03

## Context

M15 (ROADMAP 4.0 block) adds the remaining display variants of the existing chart kinds: floating
(from/to) bars, error bars and intervals, stacked and horizontal waterfalls, and sorting pie
segments by size (deferred from M9). All of them are per-chart switches, so they plug into the
option mechanism of ADRs 0012/0013: one `ChangeChart` command, one undo step each.

## Decision

- **Schema 14.** `ChartState` gains four flags, all defaulting to today's behaviour (migration 13 →
  14 adds them as `false`): `range` (column/bar only), `errors` (column/bar/line only),
  `horizontal` and `stacked` (waterfall only). Invalid combinations are rejected in
  `ChartState.__post_init__`: no `range`/`errors` on a 100 % chart, the two never combine (they
  pair data rows differently), no `range` and no `errors` with line series (line-drawn series get
  neither whiskers nor a widened scale).
- **Row pairing.** With `range=true` the series rows come in pairs: an odd data row is the *from*
  level, the row below it the *to* level of one floating bar (`datasheet.ranged`); the bar's name
  comes from the from row, an empty from cell means the baseline, a dangling unpaired last row
  stays stored and unused. With `errors=true` the same pairing holds the series value in the odd
  row and its absolute ± error magnitude in the row below (`datasheet.errored`); an empty error
  cell draws no whisker.
- **Floating bars** draw clustered (side by side per series pair), labelled with the to value
  outside the floating end, without totals; the scale covers the from levels, and arrows measure
  the to level. In range mode the grouping switches are not offered (`options.variants`).
- **Error bars** draw a whisker with caps at value ± error over every bar, clustered bar and line
  point; the scale covers value ± error. Whiskers are lines in the scheme line colour — the
  primitive model has no per-series line colour (contrast with bars).
- **Waterfall variants.** `stacked=true`: the value rows are row 1 and every used row from row 3
  down (row 2 stays the "Total" marker row); the rows stack their changes in one running total, and
  each column draws one floating segment per row (`Step.segments`), labelled with the segment's
  signed change. `horizontal=true` transposes the whole layout into the bar orientation (steps top
  to bottom, bracket lanes right of the labels, level lanes and axis below) and changes the
  same-scale orientation to "horizontal" (`samescale.orientation`).
- **Pie segment sort.** A pie joins the sortable kinds; `sorting.pie_order` returns a per-category
  permutation of the series indices (empty segments last, ties stable), display only.
  `layout_pie`/`pie_at` walk the segments in that order; labels and arrows keep their data sheet
  (category, series) indices. A pie never permutes its categories (`display_order` is the
  identity for pies), and its sort submenu is titled "Sort segments".

## Alternatives considered

- **A new chart kind for range charts** (like the waterfall): rejected — floating bars are a
  variant of the column/bar data sheet, not a different table shape, and the pairing reuses the
  "dangling index stays stored" rule.
- **Relative (percent) error bars**: not in M15; the paired row holds an absolute magnitude.
- **Rotating the vertical waterfall for the horizontal variant**: rejected — text would run
  sideways; the horizontal layout is written in bar-chart orientation instead.
- **Per-pie sort stored per category**: rejected — one `sort` order per chart, applied per pie at
  draw time, keeps the stored state unchanged by sorting (like category sorting).

## Consequences

- Schema 14 migrates stored states; every existing chart keeps its current look (all flags false).
- `datasheet.ranged`/`errored` share the pairing rule, so `range` and `errors` are mutually
  exclusive; switching to a variant that cannot hold moved labels (range, horizontal, stacked)
  clears them via the existing `_variant` rule, toggling error bars keeps them.
- Picking on floating bars uses the clustered hit tests at the to level; horizontal waterfalls
  pick steps by y (`step_at(..., horizontal=True)`).
