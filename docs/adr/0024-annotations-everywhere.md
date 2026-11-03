# 0024. Annotations everywhere: every chart kind, series pairs, gaps and brackets

- Status: accepted
- Date: 2026-11-03

## Context

M4 gave column, bar and waterfall charts difference and CAGR arrows, axis breaks and value lines
(ADR 0010); M7 extended them to line charts. Mekko, pie and scatter charts had none. An arrow could
only measure one series across two categories, and groups of categories could not be marked or
separated.

## Decision

- **Generalised arrow model (schema 13).** An arrow measures two (category, series?) points:
  `Annotation.series_end` names the series of the end (`None`: the start's series), so a
  *between-series arrow* connects two series of one category (or one series each in two). Its
  picked form follows the chart: a bracket needs side-by-side bars, so on a chart that stacks its
  series (stacked columns and bars, lines, a Mekko) a between-series bracket becomes a level
  difference (`core/picking.placed`); on a pie, whose segments meet at their arcs, a level
  difference becomes a bracket.
- **Mekko** (difference and CAGR arrows): a bracket lane above the width labels, level lanes right
  of the last column. The label measures the segment values; on a percent Mekko the shares in
  percent, so an absolute difference reads as percentage points, and no CAGR is offered (the
  column totals are all 100). The anchor meets the level the measured segment ends at — the label
  shows the segment, the geometry the level, like a stacked column.
- **Pie** (difference and CAGR arrows): between two segments, of one pie or of two. They measure
  the segments' shares in percent (percentage points); bracket anchors sit on the arcs at the
  segments' mid-angle, and between the segments of one pie only the bracket form is picked.
- **Scatter** (difference and CAGR arrows): between two points, measuring their y values; a CAGR
  counts the x distance of the two points, else their index distance.
- **Category gaps** (column and bar charts): a stored gap widens the empty space between two
  adjacent categories by a fixed amount; several per chart. Sorting that separates its categories
  hides it (stays stored, comes back with the sort order).
- **Group brackets** (column and bar charts): a bracket over a range of categories, in a lane
  above the plot (right of the outside labels on a bar chart), with a text label. The dialog asks
  for the text after the picks and again for *Change text...*; a bracket is only added with a
  label, which may be empty only through the stored state.
- **Picking** on the new kinds: Mekko segments, pie segments and scatter points are targets,
  hit-tested against the layout's own geometry (`mekko_at`, `pie_at`, `scatter_at`), like
  `column_at` and `line_at` before.

## Alternatives considered

- **Series names instead of indices** as references: names may repeat or be empty (ADR 0010).
- **Between-series CAGR** at one category: without time it can show nothing ("–"); a CAGR pick
  session therefore requires two categories, and the label guards against zero periods.
- **Cumulative segment levels as the measured view of a Mekko**: the column layout measures segment
  *values* and anchors at levels; the Mekko follows it, so its labels read like a stacked column's.
- **Category gaps on line and Mekko charts**: a line gap suggests missing data, a Mekko has fixed
  column gaps already (agreed with the maintainer).
- **Group brackets below the category names** (think-cell's place): above the plot they reuse the
  arrow lanes and stay clear of the names (agreed: above the plot).

## Consequences

- Schema 13 migrates stored states; an existing arrow keeps measuring its start series at both
  ends, and no existing chart has a group bracket to label.
- A percent Mekko is the only percent chart with annotations: difference arrows over percentage
  points.
- `sorting.remap` keeps axis annotations in place (fixes value lines on sorted charts, which were
  rejected when data category 0 moved), drops a gap whose categories sorting separates and connects
  a bracket's two end categories.
- The group bracket dialog is modal and cannot be driven by `test-lo`; it is tested by hand,
  everything behind it (model, layout, undo, persistence) without LibreOffice.
