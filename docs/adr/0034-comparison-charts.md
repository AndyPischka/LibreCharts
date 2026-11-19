# 0034. Comparison and distribution charts

- Status: accepted
- Date: 2026-11-20

## Context

The existing kinds do not answer "before vs after", "actual vs target", "which few categories
matter", "where do cases drop out" and "how wide is the spread". Five focused kinds reuse the
existing data sheet, group and renderer machinery.

## Decision

- **New kinds**: `dumbbell`, `bullet`, `funnel`, `boxplot`. Pareto is not a kind; a column or bar
  chart gains `pareto: true`.
- **Data sheets**: dumbbell uses the paired rows of floating bars (start/end), funnel the ordinary
  category/series grid, bullet and box plot fixed columns (`Label | Actual | Target | Max`,
  `Label | Min | Q1 | Median | Q3 | Max`). Parsers validate and report message keys.
- **Layouts** never add a primitive kind: markers, lines, rectangles, polygons and text are enough.
- **Pareto** sorts descending inside the layout (data sheet order breaks ties) and draws its
  cumulative percentage on a right-hand axis plus an 80 % helper line.
- Schema 19 adds `pareto`; new kind names are plain strings.

## Consequences

The five kinds appear in the menu, sidebar, deck specification and CSV export through the same
paths as the existing charts. Bullet/box plot do not take annotations in v1; the parser, not the
layout, rejects malformed sheets.
