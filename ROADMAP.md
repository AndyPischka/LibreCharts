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
| 1.0 | First release | `SECURITY.md`, packaging for extensions.libreoffice.org, German/English UI review | open |

Order is deliberate: M1 builds the shared foundation (layout, data sheet, persistence) that M2-M4 reuse.

## Later versions

Features of think-cell and empower charts that 1.0 does not cover. Each milestone gets a plan in
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
| M12 | Slide elements | Harvey balls, check marks, agenda slides, same size and arranging shapes into a grid. Plan: [slide-elements](docs/plans/slide-elements.md) | open |
| M13 | Label placement | Moving single labels by hand; the offsets survive data edits, sorting and resizing (deferred from M6) | open |

M9 comes first: its sector geometry is reused by the Harvey balls in M12, and its scatter data
sheet (one row per point, fixed columns) is the pattern the Gantt chart in M10 follows.

### 4.0: depth of analysis

| | Milestone | Content | Status |
|---|---|---|---|
| M14 | Annotations everywhere | Difference and CAGR arrows on line, Mekko, pie and scatter charts; difference arrows between series, not only between categories; category gaps and brackets over groups of categories | open |
| M15 | Range and waterfall variants | Floating (from/to) bars, error bars and intervals, stacked and horizontal waterfalls, sorting pie segments by size (deferred from M9) | open |
| M16 | Consistent rounding and decluttering | Rounded labels that add up to the rounded total; labels that overlap move apart automatically (builds on M13) | open |
| M17 | Gantt extensions | Several bars per row, working-day calendars and holidays, import from CSV and ProjectLibre (deferred from M10) | open |

### 5.0: workflow and ecosystem

| | Milestone | Content | Status |
|---|---|---|---|
| M18 | Automation | Python and macro API and a command line: build a deck from data and a template, update all data links of a presentation | open |
| M19 | Corporate design check | Check a presentation against the corporate design file of M8 (colours, fonts, positions) and fix deviations in one step | open |
| M20 | Accessibility and export | Alternative text generated from the chart data, patterns as well as colours for colour-blind readers, exporting chart data as CSV | open |
| M21 | Languages and platforms | Further UI languages through a translation platform (Weblate); macOS tested and supported | open |

Both versions are sketches. Priorities are set after 1.0 from user feedback in the issue tracker.
M18 is cheap because `core/` is plain Python. M21 changes the convention that every UI string is
German and English (AGENTS.md).

Candidates without a milestone, feasibility open: map (choropleth) charts, which need bundled
geodata of a suitable licence and size; chart templates or favourites.

## Non-goals

- **think-cell file compatibility.** No import or export of think-cell objects; the format is proprietary.
- **Writer, Calc or Draw support.** Impress only.
- **A pixel-perfect think-cell clone.** Functional equivalence, not a copy of UI or look.
- **Data from images or PDFs.** Needs OCR, a runtime dependency that ADR 0001 rules out.
- **LibreOffice Online / Collabora Online.** Python extensions are barely supported there.
