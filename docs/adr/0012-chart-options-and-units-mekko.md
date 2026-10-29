# 0012. Chart options and the units Marimekko

- Status: accepted
- Date: 2026-10-29

## Context

ADR 0009 shipped the percent Mekko only, because the units variant (column heights follow the
column sums, segments show absolute values) needs a per-chart switch the user can change after
inserting, and there was no UI for that. The sidebar (ADR 0011) and the context menu now exist.
Later milestones need more switches of this kind (100 % columns, stacked/clustered, ...).

## Decision

Agreed with the maintainer in `docs/plans/units-mekko.md`:

- **State**: `ChartState.percent` (bool, schema version 4). Only a Mekko may be `True`; for other
  kinds it stays `False` and has no meaning. Migration v3 -> v4 sets `percent` for every existing
  Mekko, so old charts stay percent Mekkos. A new Mekko starts as a percent Mekko.
- **Command**: `org.librecharts:ChangeChart?percent=true|false` (`core/options.py` parses the
  query and offers the switch for a chart). It stores the new state through `chart.redraw`: one
  undo step. Further options extend `options.changed` and `options.toggle`.
- **UI**: a toggle entry right below "Edit chart data" in the context menu and a button in the
  sidebar's "selected chart" section, only for charts that have an option. The status line names
  the variant. Insert stays one entry (a percent Mekko); there is no separate units insert.
- **Layout** (`layout_mekko(..., percent)`): the units variant scales column heights on a "nice"
  scale from zero to the tallest column sum, segments show absolute values, the column sum stands
  above each column and the width value below the category name (the plot gets one label band
  less height). Widths are unchanged: the "Width" row, else the column sum.
- The structure of the layout depends on data and variant, never on size (ADR 0007).

## Alternatives considered

- **A chart kind `mekko_units`**: no migration, but switching would change the kind and every kind
  check would need both.
- **Width above, no totals**, or **equal widths without a width row** in the units variant: the
  column sum is the only value that says what a column stands for, and the width rule should not
  change when the variant does.
- **A separate "Insert units Mekko" entry**: a second insert path for what the switch already does.

## Consequences

- A document saved with schema 4 cannot be read by an older LibreCharts ("saved by a newer
  LibreCharts"); the shapes still display (ADR 0002).
- Units Mekkos have no value axis, like the other charts; column heights are read from the labels.
- Mekko charts still have no annotations (ADR 0010).
