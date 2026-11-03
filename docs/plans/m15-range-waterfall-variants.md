# M15: Range and waterfall variants

Plan for the M15 milestone (ROADMAP 4.0 block): floating (from/to) bars, error bars and
intervals, stacked and horizontal waterfalls, and sorting pie segments by size (deferred from
M9).

## Goal

Four display variants on top of the existing chart kinds, each a per-chart switch in the context
menu and sidebar like the M5 options (ADR 0013): every switch is one `ChangeChart` command and one
undo step, and every variant survives data edits, resizing, copying and ODP/PPTX round trips like
the current layouts.

1. **Floating (from/to) bars** on column and bar charts: a bar drawn between two levels instead
   of from the baseline. These are also the *interval* bars of the roadmap entry.
2. **Error bars** on column, bar and line charts: a whisker with caps at value ± error over every
   bar, cluster and line point.
3. **Waterfall variants**: a *horizontal* waterfall (bars run left to right, like the bar layout)
   and a *stacked* waterfall (several step rows in the data sheet stack their changes in one column
   per category).
4. **Pie segment sorting**: sort the segments of each pie by size, display only, like the category
   sort of column and bar charts.

Not in M15: error bars on scatter and Mekko, floating bars on Mekko, ranges combined with 100 %
charts, error bars combined with floating bars, anything of M16-M21.

## Approach

### 1. Model and schema (`core/model.py`, `core/state_io.py`)

Four new `ChartState` fields, all defaulting to today's behaviour:

- `range: bool = False` — floating bars on column and bar charts. Only with `grouping` in
  ("stacked", "clustered"), never with `percent` and never with `lines`.
- `errors: bool = False` — error bars on column, bar and line charts. Not with `range` (the row
  pairing would collide), not with `percent`.
- `horizontal: bool = False` — waterfall only.
- `stacked: bool = False` — waterfall only; `stacked=False` is today's single-running-total
  waterfall.

Validation in `__post_init__` mirrors the existing rules (wrong kind, or an impossible
combination, raises `ValueError`). Schema 13 → 14: migration adds all four flags as `false`, so
old states draw unchanged.

### 2. Data sheet conventions (`core/datasheet.py`, `core/waterfall.py`)

- **Floating bars**: with `range=true` the series rows come in pairs — an even data row is the
  *from* level, the odd row below it the *to* level of one floating bar (series names come from the
  from row). A dangling unpaired last row stays stored and unused, like any dangling index after a
  data edit. `datasheet.parse` gains a `ranged(data)` view returning `ChartData` of the *to*
  values plus a parallel grid of *from* values; the column and bar layouts read both.
- **Error bars**: with `errors=true` the row directly below each series row holds that series'
  error magnitude (absolute ± value); an empty cell means no whisker for that point. Same pairing
  rule as `range`, hence the two are mutually exclusive.
- **Stacked waterfall**: `parse_waterfall` gains a series dimension — with `stacked=true`, rows 2
  .. n are step series; row 3's "total" marks apply per column as today. Each category's column
  stacks one floating segment per series, from the running total before that series' change to
  after it.

### 3. Layout (`core/layout/`)

All layouts keep the invariant that the kinds and order of primitives depend only on the data and
options, never on the size (ADR 0007), and keep raising `ValueError` when the box is too small.

- **`column.py` / `bar.py`**: with `range` a bar is the rect between `y(from)` and `y(to)` instead
  of baseline to `y(to)`; labels sit outside the floating end (above a rising bar, below a falling
  one, like the waterfall labels); totals are not drawn in range mode; sorting, category gaps,
  group brackets and arrows keep working — an arrow on a floating bar measures the `to` level.
  With `errors` a whisker (line plus two cap lines) is drawn per non-empty point in the series
  colour, on top of the bars; on line charts the whisker sits on the markers.
- **`line.py`**: error whiskers per point when `errors=true`.
- **`waterfall.py`**: `horizontal=true` transposes the layout (steps top to bottom, values left
  to right, labels right of the bars, connectors vertical, bracket lanes right of the labels, level
  lanes below the plot) reusing the bar layout's band constants. `stacked=true` draws one segment
  per series row per category, with connectors between segments of one column and between
  columns; `_series` gains per-segment colouring (increase/decrease/total of the segment's change).
- **`pie.py`**: segment order per pie comes from `sorting.pie_order`; angles, labels, arcs and
  `pie_at` all walk the segments in that display order. Labels, arrows and `LabelKey`s keep their
  data sheet (category, series) indices, so sorting never touches stored state — the same rule as
  category sorting.

### 4. Options and sorting (`core/options.py`, `core/sorting.py`)

- `options.variants` gains: column/bar — *Floating bars* (`range=true/false`) and *Error bars*
  (`errors=true/false`); waterfall — *Horizontal* (`horizontal=...`) and *Stacked*
  (`stacked=...`); `options.changed` handles the four new keys with the same validation.
  Switching to a variant that cannot hold moved labels (e.g. to `range`) clears them via the
  existing `_variant` rule.
- `SORTABLE` gains `"pie"`; `options._sort` accepts pie. `sorting.pie_order(data, sort)` returns a
  per-category permutation of the series indices (empty segments last, ties keep data sheet
  order), descending and ascending like `sorting.order`.

### 5. UI (`core/menu.py`, `core/panel.py`, `core/messages.py`, `lo/`)

- Context menu and sidebar show the new switches through `options.variants`; the pie chart gains
  the sort submenu through `options.sort_options`. All strings German and English in
  `messages.py`.
- No new commands: everything is a `ChangeChart?...` query through the existing
  `lo/commands.py` path, one undo step each (`lo/chart.py`, `lo/undo.py` unchanged).
- No new pick flows: annotations on floating bars and stacked waterfalls reuse the existing
  hit tests with the `to`/end level as the measured value.

## Affected modules

| Layer | Module | Change |
|---|---|---|
| core | `model.py` | `range`, `errors`, `horizontal`, `stacked` fields + validation |
| core | `state_io.py` | schema 14 + migration, new fields in JSON |
| core | `datasheet.py` | `ranged` view, error-row pairing |
| core | `waterfall.py` | stacked waterfall parsing (series dimension) |
| core | `layout/column.py`, `bar.py` | floating bars, error whiskers |
| core | `layout/line.py` | error whiskers |
| core | `layout/waterfall.py` | horizontal orientation, stacked segments |
| core | `layout/pie.py` | per-pie segment order in layout and `pie_at` |
| core | `options.py`, `sorting.py` | new switches, `pie_order`, pie in `SORTABLE` |
| core | `menu.py`, `panel.py`, `messages.py` | entries, strings (de + en) |
| tests | `tests/`, `tests/lo/` | see test strategy |

Docs: new ADR 0025 (range/error/waterfall-variant model and data sheet pairing) after
implementation; glossary terms (*floating bar*, *error bar*, *stacked waterfall*, *horizontal
waterfall*, *segment order*); ARCHITECTURE.md module rows; CHANGELOG; ROADMAP status.

## Work packages

1. Model, schema 14, options, `sorting.pie_order` (core only).
2. Floating bars: `datasheet.ranged`, column/bar layouts, labels, arrows.
3. Error bars: column, bar and line layouts.
4. Waterfall variants: stacked parsing, horizontal and stacked layouts.
5. Pie segment sorting: `layout/pie.py`, `pie_at`, menu.
6. UI strings, integration tests, docs (ADR, glossary, CHANGELOG, ROADMAP).

Each package ends with `uv run poe check` green; packages touching `lo/` additionally with
`uv run poe test-lo`.

## Test strategy

- **core** (`tests/`): validation of the new fields and impossible combinations; schema 14
  migration; `ranged` pairing (odd row counts, empty cells); error-row pairing; stacked
  `parse_waterfall` (running totals per series, totals, gaps); column/bar layouts of floating
  bars (rect between from/to, label side, no totals, arrows measure the `to` level) and error
  whiskers (positions, caps, empty error cell) at several sizes with the same primitive structure;
  horizontal waterfall (transposed bands, connectors) and stacked waterfall (segment stacking,
  colours); pie layouts with each sort order (segment angles, labels, `pie_at`, arrows) and
  several sizes; `pie_order` permutations; menu/panel contents; every new string in English and
  German. Coverage of `core/` stays >= 90 %.
- **lo** (`tests/lo/`, real LibreOffice): switching each variant through a dispatched
  `ChangeChart` command with undo/redo; re-layout after resize in each variant; PPTX round trip of
  a schema-14 state; sorting a pie; editing the data sheet of a stacked waterfall.

## Decisions

Proposed for agreement with the maintainer:

1. **Row pairing** for `range` (from/to) and `errors` (value/error) is the data sheet convention;
   the two are mutually exclusive because they pair rows differently.
2. **Floating bar labels** show the `to` value outside the floating end; totals are not drawn in
   range mode.
3. **Error bars** show an absolute ± magnitude from the paired row, whiskers with caps in the
   series colour; no relative (percent) errors in M15.
4. **Stacked waterfall** stacks per-series change segments in one column per category; the
   horizontal waterfall is the same layout transposed, not a new chart kind.
5. **Pie sorting** permutes segments within each pie independently (per-category series
   permutation), display only; stored labels and annotations keep data sheet indices.
6. **Naming**: *floating bar* / *Schwebebalken*; *error bar* / *Fehlerbalken*; *horizontal
   waterfall* / *horizontales Wasserfalldiagramm*; *stacked waterfall* / *gestapeltes
   Wasserfalldiagramm*.

After implementation this plan is deleted; its lasting decisions move into ADR 0025.
