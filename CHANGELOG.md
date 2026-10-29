# Changelog

All notable user-visible changes are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **Harvey balls and check marks** (*Insert Harvey ball*, *Insert check mark*, the sidebar's Elements
  section): small circles filled to 0, 25, 50, 75 or 100 %, and ticks, crosses or empty circles. The
  right-click menu of a selected element switches its state, *Next state* cycles it (also for several
  elements at once); they stay round when resized and survive copying and saving as ODP or PPTX.
- **Arranging shapes** (*Same width*, *Same height*, *Same size*, *Arrange in grid*, *Swap
  positions* in the LibreCharts menu and the sidebar): works on any selected shapes, charts included;
  one undo step each. The grid offers 2, 3 or 4 columns with 5 mm gaps.
- **Agenda** (*Insert agenda*, *Start chapter here*, *Update agenda* in the LibreCharts menu and the
  sidebar): an agenda slide with a numbered list of chapters, and before every chapter a divider
  slide with the same list and that chapter highlighted. Type the chapters on the agenda slide, one
  per line; *Start chapter here* on the first slide of a chapter inserts its divider, *Update
  agenda* renames, adds and removes chapters on every divider. A chapter is the slides after its
  divider: move a chapter by moving its slides together with the divider. Dividers repeat the
  agenda slide's title, layout and list, not its other content, and are rewritten on every update.
  Each command is one undo step; the agenda survives saving as ODP or PPTX.
- **Data links** (*Link data...* in the context menu, the sidebar or the LibreCharts menu): a chart
  takes its data from a range or a named range of a Calc, Excel or CSV file. *Update link* reads
  the selected charts' files again, *Update all links* every linked chart of the presentation, in
  one undo step and opening each file once; a file you have open is read with its unsaved edits.
  The chart keeps the fetched values, so it still shows (and saves as ODP or PPTX) without the
  file. Files are opened hidden, read-only and without running macros. A deck moved together with
  its workbooks keeps its links. The data sheet of a linked chart is read-only (*Show chart
  data*); *Remove link* makes the chart's data editable again, *Open source* opens the file at the
  linked range. When a presentation is opened and a linked file changed since its last update, an
  info bar offers *Update now*; nothing is updated without asking.
- **Gantt charts** (*Insert Gantt chart*): a project timeline with one row per activity. The data
  sheet has the columns Activity, Start, End, Remark and Phase; its date columns show dates, and
  formulas work. Two dates give a bar, one date a milestone (a diamond with its date), any text in
  *Phase* makes the row a phase over the rows below it (bold, in its own colour), a row without dates
  is a heading. The date scale picks days, weeks, months, quarters or years by itself and shades every
  other month or year. *Add date line...* draws a dashed line at a date, *Add today line* at today's
  date (it stays there); rows can be sorted by start date within their phase; gridlines are optional.
- **Pie and doughnut charts** (*Insert pie chart*): one pie per category column, one segment per
  series, with the share inside or next to each segment; the context menu or the sidebar switches
  to a doughnut that shows the category sum in its hole.
- **Scatter and bubble charts** (*Insert scatter chart*): the data sheet has one row per point
  (label, X, Y, Size, Group). A number in *Size* turns a point into a bubble, a *Group* gives its
  points one colour and a legend entry. Both axes are drawn, gridlines and a value line are
  optional.
- **Butterfly charts** (*Insert butterfly chart*): the first two series as bars mirrored around the
  category names on one scale; sorting, value axis, gridlines and the same scale as bar charts work
  as for bar charts.
- **Compact sidebar**: the insert-chart and add-annotation buttons are icon-only (tooltip with the
  name) and sit side by side, as do the colour scheme buttons, so the whole panel fits without
  scrolling. The value line has its own icon.
- **Colour schemes** for the whole document: built-in *Default*, *Grey* and *High contrast* buttons
  in the sidebar's *Document* section, plus *Load scheme...* and *Save scheme...* for a corporate
  design file (JSON). The scheme sets the series palette, text, line and background colours and the
  font of every chart; new presentations use the scheme configured in the extension
  (`DefaultScheme`, default *Default*). A scheme change is one undo step and survives ODP/PPTX.
- **Series colours**: the context menu's *Series colour* submenu gives one series another palette
  colour or its default colour back (one undo step). The choice follows a later scheme change.
- **Same scale**: select several charts and choose *Use the same scale* (LibreCharts menu, toolbar
  or sidebar) so that one value has the same length in all of them, across slides. *Use own scale*
  releases the group. The shared scale is the tightest chart's natural scale, is recomputed after a
  resize or data edit, and treats an axis break as hidden while the chart is grouped.
- **Copy chart format**: *Copy chart format* remembers the selected chart's format (axis,
  gridlines, series names, number format and series colours) and *Apply chart format* applies it to
  all selected charts in one undo step.
- **Line charts** (*Insert line chart*): one line per series with a marker and a value label at every
  point and the series name right of the last point; an empty value splits the line. Markers can be
  hidden from the *Format* section.
- **Area charts** (*Insert area chart*): stacked areas, with the 100 % variant from the context menu
  or the sidebar. Negative values count as empty; value lines are the annotation they take.
- **Combination charts**: a column chart can draw single series as lines (*Series as lines* in its
  context menu), optionally on a **secondary axis** right of the plot that is scaled to those series
  and always shown. Difference and CAGR arrows can measure a line series.
- Charts can show a **value axis** with tick labels and optional **gridlines**; a 100 % chart uses
  a fixed 0..100 scale, a percent Mekko has no value axis.
- **Number formats** per chart: decimals, thousands/millions/billions with a localized suffix, and
  a unit suffix. New charts take the decimal separator and the magnitude language of the UI locale;
  an existing chart keeps them wherever it is opened.
- **Series labels** right of the last column (think-cell style) or a **legend** above the plot, so
  column, bar and Mekko charts can be read without guessing colours. New charts show labels when
  stacked, a legend when clustered, and nothing on a waterfall.
- **Value lines**: *Add value line...* draws a target value or the average of the column sums across
  the plot; a chart can have several, and existing ones are edited from the annotation list.
- Value labels on dark segments are white, for contrast (WCAG relative luminance).
- The context menu and the sidebar have a *Format* section with the axis, gridline and series-name
  switches and the number-format dialog. Every switch is one undo step.
- Column and bar charts switch between stacked, clustered and 100 % after inserting, from the
  context menu or the sidebar (one undo step each). A 100 % chart shows shares inside the
  segments and the absolute column sum outside.
- Column and bar charts can sort their categories by value (descending or ascending) without
  reordering the data sheet. Annotations stay with their category; the sort order survives data
  edits, undo, copies and ODP/PPTX files.
- Marimekko charts can be switched between percent and units: *Show with units* / *Show as 100 %*
  in the chart's context menu and the sidebar (one undo step). The units variant scales column
  heights by their sums, shows absolute values, the column sum above and the width below each column.
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
- Column, bar and waterfall charts take annotations, placed by clicking columns after choosing the
  command in the menu, the toolbar or the chart's context menu:
  - difference arrows above the columns or as a level difference right of the chart, showing the
    change in percent or as an absolute value;
  - CAGR arrows, counting the years named by the categories;
  - an axis break for the whole axis: automatic, or a lower and an upper value to cut out,
    chosen in a dialog (also changeable later). Columns reaching beyond it get a break mark and
    keep their real labels.
  On bar charts the arrows run right of and below the bars and the axis break is vertical. On
  waterfall charts an arrow measures the level a column ends at, and the axis break only cuts the
  range below all steps (it shortens the start and end columns and moves the steps down).
  Annotations follow data edits, resizing, undo, copies and ODP/PPTX files.
- The chart's context menu has a "LibreCharts" submenu: edit data, add annotations, switch or
  remove existing ones.
