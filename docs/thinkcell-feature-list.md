# think-cell feature list and LibreCharts status

A working list of think-cell's features, checked against what LibreCharts implements. We work
through the open items step by step; when an item is implemented, its status and milestone move
here and in [ROADMAP.md](../ROADMAP.md).

Sources: think-cell product pages (think-cell Charts, Core, Essentials) and user manual, 2026-11.
LibreCharts status as of 7.0 (M0-M30 done, M31 research open). think-cell is a PowerPoint add-in;
LibreCharts is an Impress extension, so "done" means functional equivalence, not identical UI
(see *Non-goals* in [ROADMAP.md](../ROADMAP.md)).

Status values: **done** (milestone), **partial**, **open**, **non-goal** (deliberately out of
scope).

Complexity values (rough effort for one developer on this codebase, including tests, `test-lo`
where `lo/` is touched, and docs):

| | Meaning |
|---|---|
| **S** | days; one module, mostly `core/` |
| **M** | about 1-2 weeks; a chart variant or one `lo/` feature |
| **L** | several weeks; spans several modules (`core/` + `lo/` + UI) |
| **XL** | a milestone of its own; new chart family or new subsystem, needs a plan in `docs/plans/` |

For done items the complexity is what the feature cost (or would cost); for open items it is the
expected effort and helps pick the next item.

## 1. Chart types

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Column and bar charts: stacked, clustered, 100 % | yes | M1, switch after insert M5 | L | done |
| Sort categories by value (Pareto sort) | yes | M5; Pareto switch M24 | M | done |
| Butterfly / tornado charts | yes | M9 | M | done |
| Floating (from/to) bars | yes | M15 | M | done |
| Error bars | yes | M15 | M | done |
| Waterfall with totals and subtotals, segments below baseline | yes | M2 | L | done |
| Stacked and horizontal waterfall | yes | M15 | M | done |
| Marimekko (percent and unit axis) | yes | M3 | L | done |
| Combine small Mekko segments into "Other" | yes | — | M | open |
| Line charts, missing values (linear interpolation) | yes | lines with gaps on empty values M7 | S | partial |
| Area and area 100 % | yes | M7 | M | done |
| Combination column + line, secondary axis | yes | M7 | L | done |
| Pie and doughnut | yes | M9 | M | done |
| Gauge, pie-of-pie, concentric doughnuts, break-out slices | yes | — | M | open |
| Scatter and bubble charts | yes | M9 | M | done |
| Scatter shading / partitions (scenario, heatmap background) | yes | heatmap cells in tables M25 | M | partial |
| Gantt / project timeline: bars, milestones, phases, calendar scales | yes | M10, extensions M17 | XL | done |
| Gantt working-day calendars, holidays, CSV / ProjectLibre import | yes | M17 | L | done |
| Candlestick / football-field charts (line-chart variants) | yes | — | M | open |
| Dumbbell / slope, bullet, funnel, box plot | yes (newer versions) | M24 | L | done |
| Sankey, treemap, choropleth maps, small multiples | planned | M31 research plan | XL | open |

## 2. Labels, annotations and decorations

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Value labels and totals | yes | M1 | M | done |
| Series labels or legend | yes | M6 | S | done |
| Difference arrows: absolute / percent, bracket / level | yes | M4, everywhere M14 | L | done |
| Difference arrows between series | yes | M14 | M | done |
| CAGR arrows | yes | M4, M14 | S | done |
| Axis breaks (automatic or range) | yes | M4 | M | done |
| Value lines: target, average | yes | M6 | S | done |
| Value lines: median, net lines | yes | — | S | open |
| Category gaps and group brackets | yes | M14 | M | done |
| Move single labels by hand (persistent offsets) | yes | M13, M22 | L | done |
| Hide / rewrite / reset single labels, focus mode | yes (newer versions) | M22 | M | done |
| Callouts and source line | yes | M22 | S | done |
| Automatic decluttering of overlapping labels | yes | M16 | M | done |
| Consistent rounding (labels add up to the total) | yes | M16 | M | done |
| Number formats: decimals, magnitude suffixes, unit suffix | yes | M6 | S | done |
| Manual axis limits, tick interval, axis titles | yes | M23 | M | done |
| Logarithmic axis | yes | M23 (line, scatter) | S | done |
| Trendlines, forecasts, R², confidence band | yes | M23 | M | done |

## 3. Styling and consistency

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Colour schemes / think-cell style file | yes | M8 (scheme files, built-in schemes) | M | done |
| Per-series colour override | yes | M8 | S | done |
| Same scale across charts (works with axis breaks) | yes | M8 | M | done |
| Copy chart format to other charts | yes | M8 | S | done |
| Chart templates (kind, options, format, sample data) | yes (40+ templates) | M27 | M | done |
| Patterns beside colours (colour-blind, B/W print) | yes | M20 | M | done |
| Per-chart font size, legend placement | yes | M22 | S | done |
| Corporate design check and one-step fix | yes | M19, extended M30 | L | done |

## 4. Data and links

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Embedded datasheet per chart, live edit, formulas | yes | M1 (Calc window) | XL | done |
| Data links to external Excel/Calc/CSV ranges, manual or auto update, moved-file handling | yes | M11, update on open M28 | L | done |
| Info bar when linked sources changed | yes | M11 | S | done |
| Slide workbook: one shared dataset for several elements on a slide | yes | M28 (shared source for several charts) | M | done |
| Import CSV / ODS / XLSX into a datasheet; chart from copied cells | yes | M28 | M | done |
| Link arbitrary text fields / in-line data fields to cells | yes | — | M | open |
| Tableau links | yes | — | — | non-goal (proprietary service) |
| Chart scanner: rebuild a chart from an image | yes | — | — | non-goal (needs OCR; ADR 0001 rules out runtime dependencies) |
| Export chart data as CSV | (via datasheet) | M20 | S | done |

## 5. Slide elements (think-cell Core / Essentials)

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Harvey balls and checkboxes / check marks | yes | M12 | S | done |
| Styled data-driven tables (striping, Harvey balls in cells, sparklines, heatmap) | yes | M25 | L | done |
| Data table under / beside a chart | yes | M25 | M | done |
| 2×2 matrix with labelled axes and quadrants | yes | M25 | M | done |
| Process flows: pentagon / chevron, pyramid, auto-layout text boxes | yes | M26 | M | done |
| Agenda with chapters and divider slides, page numbers | yes | M12 | M | done |
| Arrange: align edges/centres, distribute, same size, grid, swap | yes | M12, M26 | M | done |
| Built-in icon set | yes (think-cell Library) | small built-in set M26 | L for a real library | partial (full library non-goal) |

## 6. Automation and governance

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Build decks from template + data (VBA / Python API, JSON) | yes | M18 (`librecharts.api`, `poe deck`, dispatch commands) | XL | done |
| Update all data links of a presentation | yes | M18 | M | done |
| Command-line / headless operation | via API | `poe deck build / update / check` M18 | M | done |
| Export a deck as a specification; audit a deck | partially | M29 | L | done |
| Batch format and data operations | yes | M29 | M | done |
| Corporate design check incl. master slides, report dialog | yes | M30 | L | done |

## 7. Accessibility

| Feature | think-cell | LibreCharts | Complexity | Status |
|---|---|---|---|---|
| Alternative text generated from chart data | limited | M20, every element M30 | M | done |
| Colour-blindness simulation | yes | M30 | S | done |
| Patterns for colour-blind readers | yes | M20 | M | done |

## 8. Deliberate non-goals

From [ROADMAP.md](../ROADMAP.md): no think-cell file compatibility (proprietary format), Impress
only (no Writer/Calc/Draw), functional equivalence instead of a pixel-perfect clone, no data
from images/PDFs (OCR), no LibreOffice Online. think-cell AI features (AI Suite, Assist) have no
open-source counterpart and stay out of scope.

## How to use this list

- Pick the next open item (complexity S/M first if the goal is quick wins, XL items get a plan in
  `docs/plans/`), write a plan to `docs/plans/` (see
  [docs/plans/README.md](plans/README.md)), implement, then move the status here and add a
  milestone entry to [ROADMAP.md](../ROADMAP.md).
- Priorities come from user feedback in the issue tracker.
