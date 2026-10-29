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

Features of think-cell and empower charts that 1.0 does not cover. Not yet planned in detail;
each milestone gets a plan in `docs/plans/` before work starts.

### 2.0: complete the existing charts

| | Milestone | Content | Status |
|---|---|---|---|
| M5 | Chart options | Switching column and bar charts between stacked, clustered and 100 % after inserting; sorting categories by value (ADR 0013) | done |
| M6 | Axes, labels and legend | Value axis and gridlines, number formats (decimals, thousands/millions, unit suffix), series labels or legend, value lines (target, average), label colour contrast (ADR 0014) | done |
| M7 | Line, area and combination | Line charts, stacked and 100 % area charts, column + line combination with a secondary axis (ADR 0015) | done |
| M8 | Consistency and styling | Same scale across charts, colour schemes and corporate design files, series colours, copying the format of one chart to others. Plan: [consistency-styling](docs/plans/consistency-styling.md) | open |

M5 extends the option mechanism of ADR 0012 (per-chart switches in the context menu and sidebar)
that the later milestones use; M6 then gives every chart type the same axis and label options.
The plans are drafts until agreed.

### 3.0: new areas

| | Milestone | Content | Status |
|---|---|---|---|
| M9 | Further chart types | Pie and doughnut, scatter and bubble charts, butterfly (mirrored bar) charts | open |
| M10 | Gantt / timeline | Date-scaled timeline with bars, milestones, brackets and labels per row; data in the Calc data sheet | open |
| M11 | Data links | Link a chart to a range in an external Calc or Excel file and update it on demand | open |
| M12 | Slide elements | Harvey balls, check marks, agenda slides, aligning and distributing shapes into a grid | open |

## Non-goals

- **think-cell file compatibility.** No import or export of think-cell objects; the format is proprietary.
- **Writer, Calc or Draw support.** Impress only.
- **A pixel-perfect think-cell clone.** Functional equivalence, not a copy of UI or look.
