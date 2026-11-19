# Roadmap

Vision: a free, functional counterpart to think-cell and empower charts inside LibreOffice Impress.
Single tasks live in the issue tracker, not here.

## Milestones

| | Milestone | Content | Status |
|---|---|---|---|
| M0 | Foundation | Repo scaffold, `check` + CI, `.oxt` build, menu entry with placeholder shape | done |
| M1 | Column and bar charts | Stacked and clustered column charts; Calc data sheet with live sync; chart persistence (ODP and PPTX); copies; toolbar; bar charts; re-layout on resize; `test-lo` in CI against 25.8.7; double-click to edit | done |
| M2 | Waterfall | Bridge chart with subtotals (ADR 0008) | done |
| M3 | Marimekko | Percent Mekko with variable column widths (ADR 0009); units Mekko and the per-chart option switch (ADR 0012) | done |
| M4 | Annotations | Difference arrows (bracket and level), CAGR arrows, axis break, placed by clicking columns, on column, bar and waterfall charts (ADR 0010); total labels came with M1 | done |

Order is deliberate: M1 builds the shared foundation (layout, data sheet, persistence) that M2-M4 reuse.
The first release (4.0) shipped after M17, 5.0 after M21.

## Later versions

Features of think-cell and empower charts that M0-M4 do not cover. Each milestone gets a plan in
`docs/plans/` before work starts.

### 2.0: complete the existing charts

| | Milestone | Content | Status |
|---|---|---|---|
| M5 | Chart options | Switching column and bar charts between stacked, clustered and 100 % after inserting; sorting categories by value (ADR 0013) | done |
| M6 | Axes, labels and legend | Value axis and gridlines, number formats (decimals, thousands/millions, unit suffix), series labels or legend, value lines (target, average), label colour contrast (ADR 0014) | done |
| M7 | Line, area and combination | Line charts, stacked and 100 % area charts, column + line combination with a secondary axis (ADR 0015) | done |
| M8 | Consistency and styling | Same scale across charts, colour schemes and corporate design files, series colours, copying the format of one chart to others (ADRs 0016, 0017) | done |

M5 extends the option mechanism of ADR 0012 (per-chart switches in the context menu and sidebar)
that the later milestones use; M6 then gives every chart type the same axis and label options.

### 3.0: new areas

| | Milestone | Content | Status |
|---|---|---|---|
| M9 | Further chart types | Pie and doughnut, scatter and bubble charts, butterfly (mirrored bar) charts (ADR 0018) | done |
| M10 | Gantt / timeline | Date-scaled timeline with bars, milestones, phases and labels per row; data in the Calc data sheet; date and today lines (ADR 0019) | done |
| M11 | Data links | Link a chart to a range in an external Calc or Excel file (or CSV) and update it on demand; relative paths, read-only data sheet, info bar when sources changed (ADR 0020) | done |
| M12 | Slide elements | Harvey balls, check marks, same size and arranging shapes into a grid (ADR 0021); an agenda with a divider slide before every chapter (ADR 0022) | done |
| M13 | Label placement | Moving single labels by hand; the offsets survive data edits, sorting and resizing (deferred from M6, ADR 0023) | done |

M9 comes first: its sector geometry is reused by the Harvey balls in M12, and its scatter data
sheet (one row per point, fixed columns) is the pattern the Gantt chart in M10 follows.

### 4.0: depth of analysis

| | Milestone | Content | Status |
|---|---|---|---|
| M14 | Annotations everywhere | Difference and CAGR arrows on line, Mekko, pie and scatter charts; difference arrows between series, not only between categories; category gaps and brackets over groups of categories (ADR 0024) | done |
| M15 | Range and waterfall variants | Floating (from/to) bars, error bars and intervals, stacked and horizontal waterfalls, sorting pie segments by size (deferred from M9) | done |
| M16 | Consistent rounding and decluttering | Rounded labels that add up to the rounded total; labels that overlap move apart automatically (builds on M13) | done |
| M17 | Gantt extensions | Several bars per row, working-day calendars and holidays, import from CSV and ProjectLibre (deferred from M10) | done |
| 4.0 | First release | `SECURITY.md`, packaging for extensions.libreoffice.org | done |

### 5.0: workflow and ecosystem

| | Milestone | Content | Status |
|---|---|---|---|
| M18 | Automation | Python and macro API and a command line: build a deck from data and a template, update all data links of a presentation | done |
| M19 | Corporate design check | Check a presentation against the corporate design file of M8 (colours, fonts, positions) and fix deviations in one step (ADR 0029) | done |
| M20 | Accessibility and export | Alternative text generated from the chart data, patterns as well as colours for colour-blind readers, exporting chart data as CSV (ADR 0030) | done |
| M21 | Languages and platforms | Further UI languages through a translation platform (Weblate); macOS tested and supported (ADR 0031) | languages done; macOS supported, CI job pending |

Priorities are set from user feedback in the issue tracker. M21 changed the convention that every
UI string is German and English (AGENTS.md): those two stay required, further languages come
through Weblate (ADR 0031).

### 6.0: the message on the slide

| | Milestone | Content | Status |
|---|---|---|---|
| M22 | Labels and emphasis | Hide, rewrite or reposition single labels; a focus mode that mutes the rest; callouts and a source line; font size and legend placement (builds on ADR 0023) | planned |
| M23 | Axes and trends | Manual axis limits, tick interval and axis titles; a logarithmic axis; trendlines and forecasts with R² and an optional confidence band | planned |
| M24 | Comparison and distribution charts | Dumbbell/slope, bullet, Pareto, funnel and box plot charts, reusing the scatter, floating-bar and column layouts | planned |
| M25 | Table and matrix | A styled table element with Harvey balls, check marks, sparklines and heatmap cells; a data table under a chart; a 2×2 matrix with labelled axes and quadrants | planned |
| M26 | Layout tools | Distribute shapes evenly, equal gaps, align edges and to the slide; process, pyramid and chevron graphics; a built-in icon set | planned |
| M27 | Chart templates | Save a chart's kind, options, format, colours, annotations and sample data as a template; insert it from the sidebar or the command line | planned |

Plans: [M22](docs/plans/labels-and-emphasis.md), [M23](docs/plans/axes-and-trends.md),
[M24](docs/plans/comparison-charts.md), [M25](docs/plans/table-and-matrix.md),
[M26](docs/plans/layout-tools.md), [M27](docs/plans/chart-templates.md).

### 7.0: data, automation and governance

| | Milestone | Content | Status |
|---|---|---|---|
| M28 | Data workflow | Import CSV, ODS or XLSX into any data sheet; insert a chart from copied cells; update data links on open; one shared source for several charts | planned |
| M29 | Automation round-trip and audit | Export an existing deck as a deck specification; audit a deck (charts, links, stale sources, design deviations, support data) with jump-to-slide; batch format and data operations | planned |
| M30 | Design and accessibility | Extend the corporate design check to master slides, layouts and pictures; a report dialog; theme colours and fonts; colour-blindness simulation; alternative text for every element; a palette editor | planned |

Plans: [M28](docs/plans/data-workflow.md), [M29](docs/plans/automation-roundtrip.md),
[M30](docs/plans/design-and-accessibility.md).

### Research

| | Topic | Content | Status |
|---|---|---|---|
| M31 | Flow, hierarchy and motion | Sankey and treemap charts; map (choropleth) charts, which need bundled geodata of a suitable licence and size; small multiples; a series-by-series build on a slide; diagnostics for large decks | open |

Plan: [M31](docs/plans/research-flow-hierarchy-motion.md).

6.0 and 7.0 are sketches like the versions before them: their order follows the value for a
typical deck, not a delivery date. Each milestone gets a plan in `docs/plans/` before work starts.

## Non-goals

- **think-cell file compatibility.** No import or export of think-cell objects; the format is proprietary.
- **Writer, Calc or Draw support.** Impress only.
- **A pixel-perfect think-cell clone.** Functional equivalence, not a copy of UI or look.
- **Data from images or PDFs.** Needs OCR, a runtime dependency that ADR 0001 rules out.
- **LibreOffice Online / Collabora Online.** Python extensions are barely supported there.
