# 0026. Consistent rounding and decluttering

- Status: accepted
- Date: 2026-11-04

## Context

M16 (ROADMAP 4.0 block) makes the labels of a chart trustworthy in two ways. First, where value
labels are the parts of a shown total, rounding each label on its own drifts away from the total:
three segments of a third each labelled `33%` next to a total of `101%`. Second, labels that
overlap are hidden today: a segment too small to hold its label sets `Text.hidden` (ADR 0023),
so a flat segment of a stacked column shows nothing at all. ADR 0023 announced the fix for M16:
"automatic placement and overlap removal will move labels out of segments itself" — without a
leader line, which would change the primitive structure (ADR 0007) and break the in-place redraw
and LibreOffice's undo of a drag.

## Decision

- **Largest remainder rounding (`core/rounding.py`).** `consistent(values, total, fmt)` returns the
  segment labels of one column: every value scaled by the format's magnitude and rounded at the
  format's precision — the same default `format_value` draws, decided once for the whole column
  (integral values plain, others two decimals) — so that the rounded segments sum to the rounded
  total; the leftover units go to the largest fractional remainders, ties to the earlier series.
  `consistent_shares(values, total, fmt)` does the same for percentages, so the shares of one
  column or pie sum to exactly 100 %. `None` values keep their place without a label.
- **Applied where a total is shown.** Stacked columns and bars (segments and total), 100 % columns
  and bars, percent Mekkos and pies (shares). Not applied where no sum is shown: clustered, line,
  scatter and area charts, waterfalls (step labels are changes, not parts), Gantt charts.
- **Flat segments label outside (`layout/column.py`, `layout/bar.py`).** A segment below
  `MIN_SEGMENT_FOR_LABEL` no longer hides its label: the label moves into the lane of the
  total — above the column's top edge, one `LABEL_HEIGHT` per label, the total on top (right
  of the bar end for bars, one label width per label, the total last) — as plain text without
  a segment fill. A negative segment labels at the column's bottom edge (left of the bar's
  left end); the total joins the lane of the positive end unless the column has no positive
  segment, so an all-negative column carries its total below it (left of a negative bar).
  The slot index of a flat label is data-only, and every label stays right after its segment
  in the primitive sequence, so the structure stays independent of the size (ADR 0007) and a
  resize that flips a segment across the threshold re-lays out in place. A lane that grows
  past the chart box moves back as a whole (`common.spread`, `common.spread_back`): a shape
  outside the box would grow the chart group on every redraw (the invariant of
  `test_layout_chart`), so a long lane covers the column or bar it labels instead.
- **Line labels spread per category (`layout/line.py`).** The labels above the points of one
  category are collected and moved apart with `common.spread` (the lowest keeps its place, the
  others move up); labels below negative points stay as they are.
- **Pie labels spread per side (`layout/pie.py`).** The outside labels of one side of a pie (left
  and right half) move apart vertically with `common.spread`; inside labels keep their places.
- **No state, no schema change.** Both features are computed at layout time; no `ChartState`
  field, no command, no undo step of their own. A label the user moved (ADR 0023) keeps winning:
  `labels.place` applies the offset after the layout.

## Alternatives considered

- **Rounding each label on its own** (the status quo): rejected — the labels contradict the total
  they belong to.
- **Rounding consistently across the whole chart** (all categories at one precision): rejected —
  the total a column's segments must match is that column's, so the precision is decided per
  column.
- **A generic overlap solver over all keyed labels**: rejected — the axis to move along differs per
  chart kind and geometry, and the three cases above (flat segments, line points, pie outside
  labels) are the overlaps that occur; each layout knows its own lane.
- **Leader lines from a moved-out label to its segment**: rejected (ADR 0023) — a line that appears
  with the placement would change the primitive structure and break in-place redraws and undo.
- **Revealing flat labels on Mekko and area charts too**: deferred — their outside placement has
  no lane yet (a Mekko column is narrow, an area has no total); they keep hiding too-small labels.

## Consequences

- Every existing chart keeps its totals consistent from now on; a chart whose labels summed
  slightly off changes its label texts (never its structure).
- A flat segment's label is drawn even when it does not fit and can be dragged (M13) like any
  other; `labels.place` still recolours a moved label for the shape under it.
- The reveal replaces the `hidden` flag of the stacked column/bar and percent layouts; Mekko and
  area layouts still hide labels of too-small segments, and `labels.place` still reveals a hidden
  label the user moves.
- The lane above a column grows with every flat label; a lane that would leave the chart box
  moves back as a whole and then covers the column or bar it labels (the line/pie spread shifts
  its whole stack back from the chart edge the same way). A column of many flat segments can
  therefore push its total lane high onto the column itself.
