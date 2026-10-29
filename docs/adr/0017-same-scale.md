# 0017. Same scale across charts

- Status: accepted
- Date: 2026-10-29

## Context

Charts on different slides often show the same unit (revenue, headcount). Readers compare their
column heights even when the charts use different value ranges, so the same value looks longer in
one chart than in another. The M8 plan asked for a way to tie charts together so that one value has
one length, across the whole document.

## Decision

Agreed with the maintainer in `docs/plans/consistency-styling.md` (recommended answers to its open
questions):

- **Group id** in the chart state: `ChartState.scale_group: str | None` (schema 8). A group spans
  the whole document; charts on any slide may share it. `None` is the chart's own scale.
- **Comparable charts**: vertical charts (column, line, area, waterfall, units Mekko) can share with
  each other; bar charts (horizontal) only with bar charts. Percent charts have a fixed 0..100 scale
  of their own and never join. The rule lives in `core/samescale.py` (`orientation`, `can_join`).
- **Length per unit** is not stored. Each chart computes its natural scale at its current size
  (`natural_length_per_unit` in every layout), and the group uses the smallest of them
  (`common_length_per_unit`). This makes the tightest chart fit and leaves empty space in the
  others. Recomputing on every layout keeps the scale right after resize, undo, redo and reload.
- **Layout**: `layout_chart(..., length_per_unit=None)` threads the value through every layout.
  Vertical charts anchor the scale at the plot bottom:
  `y(value) = top_band + scale_height - (value - axis.minimum) * length_per_unit`; bar charts anchor
  it at the plot's left edge. The axis is still computed for ticks and labels, but an axis break is
  ignored (not drawn) in a group, because a folded scale would break the shared length.
- **Adapter**: `lo/samescale.py` collects the group's charts, their states and current sizes, and
  redraws every affected chart inside one undo lock. A resize re-lays out the resized chart and its
  peers (`chart.fit_to_size`), without adding an undo step. A data edit, option change or undo
  redraws the group too.
- **Commands and UI**: `SameScale` joins the selected charts and merges their groups (one undo
  step); `RemoveSameScale` gives the selected charts and their groups their own scale again. Both
  are in the LibreCharts menu, the toolbar and the sidebar; the context menu offers "Own scale" for
  a chart in a group.
- **Axis break**: a chart keeps its stored axis break; leaving the group draws it again.

## Alternatives considered

- **Store the length per unit**: it goes stale as soon as a chart is resized, undone or edited; the
  smallest natural scale is cheap to recompute and always consistent.
- **Use the largest chart's scale**: the smaller charts would clip their columns; the tightest chart
  sets the limit.
- **Align the plot areas or axis maxima**: equal plot heights do not make a value the same length
  when the value ranges differ.
- **Include percent charts**: their 0..100 scale means something else; mixing them with absolute
  values would be misleading.
- **Mix bars and columns**: the same length would apply across orientations, but the anchoring and
  the reading direction differ; separate orientations keep the rule simple.
- **One stored absolute axis for the group**: a group with a small and a large value range would
  waste most of the small chart; the smallest natural scale adapts to the actual sizes.

## Consequences

- Charts in a group can have empty space above their columns (or right of their bars); that is the
  visible sign of the shared scale.
- Group changes redraw several charts; the adapter wraps them in one undo action, so the undo list
  stays one step per user action.
- Picking annotations still uses each layout's natural geometry; in a grouped chart a click on a
  line point can be slightly off. Picking is a M4 feature for annotations, not for reading values.
- A group id is a plain string; a document copied from another keeps its groups and their members
  as long as the charts travel together.
- The axis break is hidden while a chart is in a group; this is documented in the glossary, and no
  data is lost.
