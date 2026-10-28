# Changelog

All notable user-visible changes are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- A LibreCharts deck in the Impress sidebar: buttons to insert charts, edit the selected
  chart's data and add annotations, and the list of the chart's annotations with a remove button
  each. It follows the selection.
- Installable `.oxt` with a "LibreCharts" menu in Impress (German and English UI).
- *LibreCharts → Insert column chart* inserts a stacked column chart with sample data, drawn as native
  shapes with segment and total labels. Insert is a single undo step.
- A "LibreCharts" toolbar with icons for both commands. In the Notebookbar (ribbon) interface it
  appears in the "Extension" group.
- *LibreCharts → Insert Marimekko chart* (and a toolbar button): percent Mekko whose column widths are
  the column sums or the values of an optional "Width" row in the data sheet; shares inside, widths
  above, series names to the right.
- *LibreCharts → Insert waterfall chart* (and a toolbar button): steps float between running
  totals, columns marked in the "Total" row of the data sheet show subtotals, connectors link the
  columns and steps carry their sign.
- *LibreCharts → Insert bar chart* (and a toolbar button) inserts a horizontal bar chart with the
  same data sheet, resizing, undo and ODP/PPTX support as column charts.
- Resizing a chart lays it out again for the new size instead of stretching it; undo and redo
  of the resize work as usual.
- Copied or duplicated charts can be edited independently of the original.
- Chart data is stored in the document and survives saving as ODP and PPTX.
- *LibreCharts → Edit chart data* opens the chart's data in a Calc window. Every edit updates the
  chart immediately (one undo step each); formulas are kept when the window is closed and reopened.
- Double-clicking a chart opens its data sheet, like *Edit chart data*.
- Column charts take annotations, placed by clicking columns after choosing the command in the
  menu, the toolbar or the chart's context menu:
  - difference arrows above the columns or as a level difference right of the chart, showing the
    change in percent or as an absolute value;
  - CAGR arrows, counting the years named by the categories;
  - an axis break for the whole axis: automatic, or a lower and an upper value to cut out,
    chosen in a dialog (also changeable later). Columns reaching beyond it get a break mark and
    keep their real labels.
  Annotations follow data edits, resizing, undo, copies and ODP/PPTX files.
- The chart's context menu has a "LibreCharts" submenu: edit data, add annotations, switch or
  remove existing ones.
