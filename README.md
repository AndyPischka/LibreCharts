# LibreCharts

think-cell-style charts for **LibreOffice Impress**, as an open-source extension.
Column, waterfall and Marimekko charts with difference arrows, CAGR arrows and total labels,
drawn as native shapes and fed from a Calc data sheet.

> **Status: M0, scaffold only.** The extension installs and adds a placeholder shape;
> real charts arrive milestone by milestone, see [ROADMAP.md](ROADMAP.md).
> LibreCharts is inspired by think-cell and empower charts but is not affiliated with them and
> does not read or write their files.

## Requirements

- LibreOffice **25.8 or newer** (Windows, Linux, macOS). The minimum is documented, not enforced by the package.

## Install

1. Build the package (see below) or take `LibreCharts-<version>.oxt` from a release.
2. In LibreOffice: *Tools → Extension Manager → Add…* and pick the `.oxt`; restart LibreOffice.
3. In Impress, use the new **LibreCharts** menu.

## Develop

Requires [uv](https://docs.astral.sh/uv/).

```
uv run poe setup    # dependencies + git hooks
uv run poe check    # lint, format, types, tests (what CI runs)
uv run poe build    # dist/LibreCharts-<version>.oxt
```

More: [CONTRIBUTING.md](CONTRIBUTING.md), [ARCHITECTURE.md](ARCHITECTURE.md), [AGENTS.md](AGENTS.md) (for AI agents).

## License

[MPL-2.0](LICENSE)
