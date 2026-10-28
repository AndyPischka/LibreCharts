# LibreCharts

think-cell-style charts for **LibreOffice Impress**, as an open-source extension.
Charts are drawn as native shapes and fed from a Calc data sheet.

> **Status: M1 to M4 done.** Stacked and clustered **column and bar charts**,
> **waterfall** and **Marimekko charts** work: edit the data in
> a Calc window (formulas included), resize charts freely, undo everything, save as ODP or PPTX.
> Column charts take **difference arrows, CAGR arrows and axis breaks**. Next: the first release,
> see [ROADMAP.md](ROADMAP.md).
> LibreCharts is inspired by think-cell and empower charts but is not affiliated with them and
> does not read or write their files.

## Requirements

- LibreOffice **25.8 or newer** (Windows, Linux, macOS). The minimum is documented, not enforced by the package.

## Install

1. Build the package (see below) or take `LibreCharts-<version>.oxt` from a release.
2. In LibreOffice: *Tools → Extension Manager → Add…* and pick the `.oxt`; restart LibreOffice.
3. In Impress, use the **LibreCharts** menu or toolbar to insert a column, bar, waterfall or
   Marimekko chart; double-click a chart (or select it and choose *Edit chart data*) to change its
   data in Calc.
4. To annotate a column chart, select it and choose *Add difference arrow*, *Add level difference*
   or *Add CAGR arrow* (menu, toolbar or the chart's context menu), then click the columns as the
   bar above the slide says; `Esc` cancels. *Add axis break* opens a dialog: automatic, or the lower
   and upper value to cut out of the whole axis. The context menu of the chart switches arrows
   between percent and absolute, or bracket and level, changes the axis break and removes
   annotations.

## Develop

Requires [uv](https://docs.astral.sh/uv/).

```
uv run poe setup    # dependencies + git hooks
uv run poe check    # lint, format, types, tests (what CI runs)
uv run poe build    # dist/LibreCharts-<version>.oxt
uv run poe test-lo  # integration tests against an installed LibreOffice
```

More: [CONTRIBUTING.md](CONTRIBUTING.md), [ARCHITECTURE.md](ARCHITECTURE.md), [AGENTS.md](AGENTS.md) (for AI agents).

## License

[MPL-2.0](LICENSE)
