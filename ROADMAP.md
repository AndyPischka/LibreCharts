# Roadmap

Vision: a free, functional counterpart to think-cell and empower charts inside LibreOffice Impress.
Single tasks live in the issue tracker, not here.

## Milestones

| | Milestone | Content | Status |
|---|---|---|---|
| M0 | Foundation | Repo scaffold, `check` + CI, `.oxt` build, menu entry with placeholder shape | done |
| M1 | Column and bar charts | Stacked and clustered column charts; Calc data sheet with live sync; chart persistence (ODP and PPTX); copies; toolbar; bar charts; re-layout on resize; `test-lo` in CI against 25.8.7; double-click to edit | done |
| M2 | Waterfall | Bridge chart with subtotals (ADR 0008) | done |
| M3 | Marimekko | Percent Mekko with variable column widths (ADR 0009). Later: units (absolute) Mekko, which needs a chart option UI | done |
| M4 | Annotations | Difference arrows, CAGR arrows, total labels, axis break | open |
| 1.0 | First release | `SECURITY.md`, packaging for extensions.libreoffice.org, German/English UI review | open |

Order is deliberate: M1 builds the shared foundation (layout, data sheet, persistence) that M2-M4 reuse.

## Non-goals

- **think-cell file compatibility.** No import or export of think-cell objects; the format is proprietary.
- **Writer, Calc or Draw support.** Impress only.
- **A pixel-perfect think-cell clone.** Functional equivalence, not a copy of UI or look.
