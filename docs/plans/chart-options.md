# Plan: M5 chart options (stacked, clustered, 100 %, sorting)

Status: draft, not yet agreed (2026-10-29).

## Goal

Column and bar charts can be switched after inserting between three variants, as in think-cell:

- **Stacked** (today's default),
- **Clustered**: the layout exists (`layout/column.py`, `layout/bar.py`), but no command or menu
  reaches it today,
- **100 %**: every column (bar) is 100 % high (long), segments show shares.

Categories of column and bar charts can be **sorted** by value (descending or ascending) without
reordering the data sheet.

The units Mekko (ADR 0012) already introduced the option mechanism (`core/options.py`,
`ChangeChart`); this plan extends it from one toggle to several switches per chart.

Non-goals: options for waterfall charts, a separate insert entry per variant, an options dialog.

## Approach

### State (`core/model.py`, `core/state_io.py`)

- `percent` becomes valid for `column` and `bar` too, but only with `grouping == "stacked"`
  (`__post_init__`). A 100 % chart is a stacked chart with `percent=True`, so `grouping` and
  `percent` stay two independent fields and no migration is needed for them.
- New field `sort: Literal["none", "descending", "ascending"] = "none"`. Only `column` and `bar`
  may have another value.
- Schema version 5; migration `_v4_to_v5` adds `"sort": "none"`.

### Layout

- New `core/percent.py` (or a function in `layout/common.py`): `shares(data) -> ChartData` turns
  values into shares of their column's sum. Negative values count as empty, the same rule as the
  Mekko (`core/mekko.py`); the rule moves to a shared helper.
- `layout_column` / `layout_bar` with `percent=True`: fixed scale 0..100 %, segment labels as
  percent, the absolute column sum above (below for bars: right of) each column as `"total"`.
  The structure depends on data and variant only (ADR 0007).
- New `core/sorting.py`: `order(data, grouping, sort) -> tuple[int, ...]`, a permutation of the
  category indices. Key: the column sum (stacked, 100 %), the first series (clustered). Empty
  categories go last; ties keep the data sheet order (stable sort).
- `layout_chart` applies the permutation to `ChartData` before laying out. Annotations keep
  **data sheet indices** in the state; `layout_chart` maps `start`/`end` through the permutation,
  and `picking.py` maps a clicked display position back. So switching the sort never touches
  stored annotations, and undo stays trivial.

### Commands (`core/options.py`, `lo/commands.py`)

- `ChangeChart` accepts `grouping=stacked|clustered`, `percent=true|false` and
  `sort=none|descending|ascending`, one key per call. `options.changed` validates per kind:
  `grouping` and `sort` only for column/bar; `percent=true` on a clustered chart also sets
  `grouping=stacked` (the switch "100 %" works from every variant).
- `options.toggle` becomes `options.switches(state) -> tuple[Switch, ...]`, each with message key,
  command and whether it is the current value. The Mekko keeps its single toggle.

### UI (`core/menu.py`, `core/panel.py`, `core/messages.py`)

- Context menu of a column or bar chart, below "Edit chart data": the two variants the chart is
  not in ("Stacked" / "Gestapelt", "Clustered" / "Gruppiert", "100 %"), then a submenu
  "Sort" / "Sortieren" with "None", "Descending", "Ascending" (the current one marked or omitted).
- Sidebar, "selected chart" section: three variant buttons (current one disabled) and a sort
  button that cycles none -> descending -> ascending. New 16 px icons for the three variants.
- Status line names the variant: "Column chart (100 %)" / "Säulendiagramm (100 %)".

### Annotations

- 100 % charts: annotations stay in the state but are neither drawn nor offered (as on Mekko
  charts); switching back shows them again. `notes.SUPPORTED` gets a check on `percent`.
- Clustered -> stacked: arrows bound to one bar (`series` set) are not drawn on a stacked chart;
  `notes.drawable` gets that rule (today it would draw them).

## Affected modules

`core/model.py`, `core/state_io.py`, `core/options.py`, `core/mekko.py` (shared negative rule),
new `core/sorting.py`, `core/layout/column.py`, `core/layout/bar.py`, `core/layout/chart.py`,
`core/annotations.py`, `core/picking.py`, `core/menu.py`, `core/panel.py`, `core/messages.py`,
`lo/commands.py`, `lo/sidebar.py` (several option buttons), `extension/entry.py`,
`extension/images/` (icons).

## Tests

- `tests/core`: migration v4 -> v5; validation (`percent` on clustered, `sort` on waterfall raise);
  100 % layout (heights equal, labels as shares, totals absolute, negatives ignored, structure
  independent of size); sort order (descending, ascending, ties, empty categories); annotations
  follow a sorted category and picking maps back; switches per kind and variant; query parsing.
- `tests/lo/test_options.py`: dispatch each `ChangeChart` variant on column and bar charts ->
  stored state and shapes change, one `.uno:Undo` restores; sort survives ODP and PPTX reload and a
  data sheet edit; an arrow on a sorted chart stays on its category.

## Docs

New ADR "100 % charts and sorting" (extends ADR 0012); ARCHITECTURE.md (`sorting.py`, model
fields); glossary ("100 % chart", "Clustered", "Sort order"); CHANGELOG; ROADMAP; README.

## Open questions (recommendation first)

1. 100 % via the existing `percent` field (recommended) or a third grouping value `"percent"`
   (then the Mekko's `percent` and the column's `"percent"` would mean the same thing twice).
2. Above a 100 % column: its absolute sum (recommended, like think-cell) or nothing.
3. Annotations on 100 % charts: not in M5 (recommended) or difference arrows between shares.
4. Sort key of clustered charts: the first series (recommended) or the category sum.
5. Sort Mekko columns by width as well: later (recommended) or in M5.
