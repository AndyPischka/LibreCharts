# 0013. 100 % charts and sorting categories

- Status: accepted
- Date: 2026-10-29

## Context

ADR 0012 introduced per-chart options for the Mekko. Column and bar charts need the same kind of
switch for their three variants (stacked, clustered, 100 %), and users want to sort categories by
value without reordering the data sheet. Both are display options: the data and the annotations
must survive a switch unchanged.

## Decision

Agreed with the maintainer in `docs/plans/chart-options.md`:

- **State**: `ChartState.percent` keeps its name and now also describes a 100 % column or bar
  chart. Such a chart is always stacked (`grouping == "stacked"`); a clustered percent chart is
  rejected by the model. The new field `ChartState.sort` (`"none"`, `"descending"`,
  `"ascending"`) is valid for column and bar charts only. Schema version 5; migration v4 -> v5 adds
  `"sort": "none"`, so existing charts keep their data sheet order.
- **100 % layout**: column and bar layouts take a `percent` flag. The value scale is fixed to
  0..100, segment labels are shares (`core/percent.py`), and the absolute column sum stands above
  (right of, for bars) each column. Negative values count as empty, the same rule as the Mekko;
  the rule now lives in `core/percent.py` and the Mekko parser uses it too.
- **Sorting**: `core/sorting.py` returns a permutation of the category indices. Stacked and 100 %
  charts sort by the column sum, clustered charts by the first series. Empty categories go last,
  ties keep the data sheet order (stable sort). `layout_chart` applies the permutation to the data
  and moves annotation indices along, so the stored annotations keep data sheet indices; picking
  maps a clicked display position back. Axis breaks belong to the axis and are never remapped.
- **Commands and UI**: `ChangeChart` takes exactly one of `grouping`, `percent` or `sort` per
  call. `percent=true` on a clustered chart switches it to stacked first, so the 100 % variant works
  from every variant. The context menu offers the other variants and a sort submenu, the sidebar
  the three variant buttons (current one disabled) plus a button that cycles the sort order. The
  status line names the 100 % variant.
- **Annotations on 100 % charts**: they stay stored but are neither drawn nor offered, like on a
  Mekko. Switching back shows them again.
- Sorting a Mekko by column width is not part of this milestone.

## Alternatives considered

- **A third grouping value `"percent"`**: percent and grouping would encode the same thing twice
  and every existing grouping check would need both values.
- **No totals on 100 % charts**: the absolute column sum is the only place where the real magnitude
  remains visible.
- **Sorting by rewriting the cells**: it would change formulas and the user's data, and undo would
  have to restore the sheet.
- **Sort key of clustered charts: the column sum**: the first series keeps the bars of one category
  together in a predictable order.

## Consequences

- A document saved with schema 5 cannot be read by older builds ("saved by a newer LibreCharts");
  the shapes still display.
- A 100 % chart looks like a Mekko column chart without the variable widths; it has no annotations
  and no axis break.
- The stored sort order survives data edits, copies and ODP/PPTX files; annotations and picking
  continue to use data sheet indices.
