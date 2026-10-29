# 0009. Percent Marimekko with an optional width row

- Status: accepted; the units variant followed in [0012](0012-chart-options-and-units-mekko.md)
- Date: 2026-10-28

## Context

A Marimekko (Mekko) chart encodes a second value in the column widths, typically market size per
market, while the segments show shares within each column. think-cell offers a percent and a units
variant. The data sheet must say where widths come from without breaking the column chart layout.

## Decision

Chosen by the maintainer from the proposed options:

- **Percent Mekko only** for M3: every column is 100 % high; segments stack bottom-up in series order.
  A units variant needs a per-chart option switch, which has no UI yet.
- **Widths**: by default a column's width is the sum of its segments. An optional row directly below
  the category names whose name is "Width" or "Breite" overrides it per column; an empty or
  non-positive cell there falls back to the sum. `core/mekko.py` removes that row before parsing the
  series like a column chart.
- **Labels**: shares in percent inside the segments (empty when the segment is too flat or the column
  too narrow), the width value above each column, the category name below, the series names right of
  the last column at the height of their segments.
- **Gap**: a fixed 1 mm between columns, so equal colours of neighbouring columns do not merge; widths
  stay proportional to the data.
- Negative values count as empty. Width and category labels of narrow columns get a box of at least
  18 mm centred on the column, so names do not wrap letter by letter.
- Layout structure depends only on the data (ADR 0007).

## Alternatives considered

- Units Mekko and both variants (needs an option UI); a mandatory width row (extra row in the common
  case); always the column sum (widths could not be given independently).
- Labels with absolute values or percent plus value (crowded in small segments).
- Touching columns with white segment borders.

## Consequences

- A series named "Width" or "Breite" in the first series row is read as the width row.
- Series names follow the segments of the last column; if that column has several very thin segments,
  their names can crowd each other.
- Percent labels are rounded individually and need not add up to exactly 100.
