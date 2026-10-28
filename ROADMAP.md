# Roadmap

Vision: a free, functional counterpart to think-cell and empower charts inside LibreOffice Impress.
Single tasks live in the issue tracker, not here.

## Milestones

| | Milestone | Content | Status |
|---|---|---|---|
| M0 | Foundation | Repo scaffold, `check` + CI, `.oxt` build, menu entry with placeholder shape | done |
| M1 | Column and bar charts | Stacked and clustered column charts; Calc data sheet with live sync; chart persistence (ODP and PPTX); copies; toolbar. bar charts; re-layout on resize. Open: `test-lo` in CI, double-click to edit | in progress |
| M2 | Waterfall | Bridge chart with subtotals (ADR 0008) | done |
| M3 | Marimekko | Variable column widths, percent and absolute | open |
| M4 | Annotations | Difference arrows, CAGR arrows, total labels, axis break | open |
| 1.0 | First release | `SECURITY.md`, packaging for extensions.libreoffice.org, German/English UI review | open |

Order is deliberate: M1 builds the shared foundation (layout, data sheet, persistence) that M2-M4 reuse.

## Non-goals

- **think-cell file compatibility.** No import or export of think-cell objects; the format is proprietary.
- **Writer, Calc or Draw support.** Impress only.
- **A pixel-perfect think-cell clone.** Functional equivalence, not a copy of UI or look.
