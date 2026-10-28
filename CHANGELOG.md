# Changelog

All notable user-visible changes are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Installable `.oxt` with a "LibreCharts" menu in Impress (German and English UI).
- *LibreCharts → Insert column chart* inserts a stacked column chart with sample data, drawn as native
  shapes with segment and total labels. Insert is a single undo step.
- A "LibreCharts" toolbar with icons for both commands. In the Notebookbar (ribbon) interface it
  appears in the "Extension" group.
- Chart data is stored in the document and survives saving as ODP and PPTX.
- *LibreCharts → Edit chart data* opens the chart's data in a Calc window. Every edit updates the
  chart immediately (one undo step each); formulas are kept when the window is closed and reopened.
