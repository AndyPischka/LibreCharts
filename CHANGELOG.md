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
- *LibreCharts → Insert bar chart* (and a toolbar button) inserts a horizontal bar chart with the
  same data sheet, resizing, undo and ODP/PPTX support as column charts.
- Resizing a chart lays it out again for the new size instead of stretching it; undo and redo
  of the resize work as usual.
- Copied or duplicated charts can be edited independently of the original.
- Chart data is stored in the document and survives saving as ODP and PPTX.
- *LibreCharts → Edit chart data* opens the chart's data in a Calc window. Every edit updates the
  chart immediately (one undo step each); formulas are kept when the window is closed and reopened.
