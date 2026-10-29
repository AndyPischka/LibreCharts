# Glossary

Use these terms consistently in code, UI strings and docs.

| Term | Meaning |
|---|---|
| **Chart** | One LibreCharts object on a slide: a group of shapes plus its data. |
| **Chart state** | The persisted description of a chart: raw data sheet cells (incl. formulas), their evaluated values, chart kind, grouping and a schema version. Stored as JSON in the document. |
| **Chart id** | Short random id of a chart. The chart's group shape is named `librecharts:<id>` (its *anchor*); the chart state is stored under the same key in the document. |
| **Fork** | Giving a copied chart its own id and its own copy of the state before editing it. |
| **Orphaned chart** | A chart whose group has an anchor but whose state is missing from the document, e.g. after copying it into another presentation. It still looks right but cannot be edited. |
| **Primitive** | A rectangle, line or text box produced by layout; plain geometry in 1/100 mm that the adapter turns into a shape. |
| **Data sheet** | The Calc document in which the user edits a chart's values (ADR 0003). |
| **Bar chart** | Column chart turned by 90 degrees: categories run top to bottom, values left to right ("Balkendiagramm"). Vertical ones are *column charts* ("Säulendiagramm"). |
| **Category** | One position on the category axis (x-axis of a column chart). |
| **Series** | One set of values across categories; one colour, one legend entry. |
| **Segment** | One rectangle: the value of one series in one category. |
| **Total label** | The label above a stacked column showing the sum of its segments. |
| **Waterfall** | Bridge chart: floating steps show increases and decreases between a start and an end value. Data sheet rows: names, values, "Total" marker (ADR 0008). |
| **Subtotal** | A waterfall column (marked in the "Total" row) that shows the running total instead of a change. |
| **Step** | One change column of a waterfall, floating between the running totals before and after it. |
| **Connector** | The thin line from the end of one waterfall column to the start of the next. |
| **Marimekko (Mekko)** | Stacked chart whose column width is also data (e.g. market size); segments show percent shares (ADR 0009). |
| **Percent Mekko / Units Mekko** | The two Mekko variants: every column 100 % high with percent labels, or column heights by their sums with absolute labels (ADR 0012). |
| **Chart option** | A per-chart switch the user can change after inserting, via the context menu or the sidebar (`ChangeChart` command, `core/options.py`). |
| **Stacked / Clustered** | The two ways to place the segments of one category: on top of each other in one column, or side by side as one bar per series. |
| **100 % chart** | A stacked column or bar chart whose columns are all 100 % high; segments show their share, the absolute column sum stays above (right of, for bars) the column. Negative values count as empty (ADR 0013). A percent Mekko is the same idea with variable column widths. |
| **Line chart** | One line per series through the category centres, with a marker and a value label at every point and the series name right of the last point; an empty value splits the line (ADR 0015). |
| **Area chart** | Stacked areas: every series is one filled area between its cumulative edges. The 100 % variant shows shares of the column sums. Negative values count as empty, empty values as zero (ADR 0015). |
| **Pie chart / Doughnut** | One pie per category with one segment per series, clockwise from 12 o'clock; shares are labelled inside wide segments and outside narrow ones. A doughnut has a hole that shows the category sum (ADR 0018). |
| **Scatter chart / Bubble chart** | Points on two numeric axes read from a data sheet with one row per point (label, x, y, size, group). A point with a size is a bubble whose area is proportional to it (ADR 0018). |
| **Bubble** | The translucent circle of a bubble chart point; its diameter is layout output, unlike the fixed-size marker (ADR 0018). |
| **Butterfly chart** | Two series as bars mirrored around a central band of category names, on one common scale; further series are ignored (ADR 0018). |
| **Slide element** | A Harvey ball or check mark: a group of native shapes whose whole state is its group name (ADR 0021). |
| **Harvey ball** | A circle filled to 0, 25, 50, 75 or 100 %, drawn as an outline plus a sector. |
| **Check mark** | A tick, a cross or an empty circle; tick and cross have fixed colours. |
| **Gantt chart** | A project timeline: one row per data sheet row (label, start, end, remark, phase marker by column position), a two-level date scale on top (ADR 0019). |
| **Activity** | A Gantt row with a start and an end date, drawn as a bar from the start of its first to the end of its last day. |
| **Milestone** | A Gantt row with a single date (or start equal to end), drawn as a diamond with its date. |
| **Phase** | A Gantt row with text in the phase column: a thin bar with ticks over the rows below it; it gives them its colour. |
| **Heading row** | A Gantt row with a label but no dates: a bold label only. |
| **Time scale** | The two-level date header of a Gantt chart, e.g. weeks under months; chosen from the date range alone (ADR 0019). |
| **Date line** | A value line on a Gantt chart: a dashed vertical line at a date (a Calc serial number); the *today line* is one set to the day it was added. |
| **Data link** | A chart's tie to a range of an external spreadsheet (`ChartState.link`); the chart stores the fetched values and is updated on demand (ADR 0020). |
| **Source** | The spreadsheet file (`.ods`, `.xlsx`, `.xls`, `.csv`) a linked chart takes its data from. |
| **Update (a link)** | Read the linked range of the source again and redraw the chart if its data changed; *Update all links* does it for every linked chart of the presentation in one undo step. |
| **Combination chart** | A column chart with single series drawn as lines (`ChartState.lines`), optionally on a secondary axis (`secondary`); line series are left out of stacking, clustering and picking (ADR 0015). |
| **Secondary axis** | The right-hand value axis of a combination chart, scaled to its line series only. It is always drawn, even when the chart's value axis is off (ADR 0015). |
| **Marker** | The fixed-size dot on a line point; switched on or off per chart in the format (ADR 0015). |
| **Sort order** | Display order of the categories of a column or bar chart by value: data sheet order, descending or ascending. It never changes the data sheet or the stored annotation indices (ADR 0013). |
| **Chart format** | The per-chart look stored in `ChartState.format`: value axis, gridlines, series names, decimals, magnitude, unit, decimal separator and language (ADR 0014). |
| **Colour scheme** | The document-wide look stored as `librecharts:scheme`: series palette, text, line and background colour, font name and size. Built-in Default, Grey and High contrast, or a JSON file (ADR 0016). |
| **Palette** | The list of series colours in a colour scheme; a series index wraps around it. |
| **Series colour** | A per-series palette index in `ChartState.colors` (`None`: the series' own palette entry), set through the context menu (ADR 0016). |
| **Copy chart format** | Take one chart's `Format` and series colours and apply them to other selected charts, without touching their data (ADR 0016). |
| **Same-scale group** | Charts tied together by `ChartState.scale_group` so that one value unit has the same length in all of them, across the document (ADR 0017). |
| **Length per unit** | How many 1/100 mm one value unit gets; a same-scale group uses the smallest natural length of its charts (ADR 0017). |
| **Value axis** | The scale beside (below, for bar charts) the plot with one tick label per tick. Optional; a 100 % chart uses 0..100, a percent Mekko has none (ADR 0014). |
| **Gridlines** | One light line per axis tick across the plot, behind the segments; only drawn together with the value axis. |
| **Series labels** | The series names right of the last column, each level with its segment (think-cell style). |
| **Legend** | The series names with a colour swatch above the plot. |
| **Number format** | Decimals, magnitude and unit suffix applied to every value label; shares use decimals and separator only (ADR 0014). |
| **Magnitude** | The power of ten values are divided by (thousands, millions, billions) with a localized suffix such as "Tsd." or "k" (ADR 0014). |
| **Value line** | A dashed line across the plot at a target value or at the average of the column sums, with its label; a chart may have several (ADR 0014). |
| **Width row** | Optional Mekko data sheet row named "Width"/"Breite" right below the category names; sets column widths. |
| **Annotation** | An arrow or axis break the user placed on a chart; stored in the chart state by category index (ADR 0010). |
| **Difference arrow** | Annotation that shows the relative ("+25%") or absolute ("+5") difference between two columns, or two bars of one series. Drawn as a *bracket* (above columns, right of bars) or as a *level difference*. On a waterfall chart it measures the level a column ends at. |
| **Level difference** | Difference arrow drawn right of the plot (below it on bar charts): dashed lines at the values of both columns, an arrow between them. |
| **CAGR arrow** | Annotation that shows the compound annual growth rate between two columns, over the years named by the categories (else the number of columns between them). |
| **Sidebar deck** | The LibreCharts tab of the Impress sidebar; its one panel mirrors the menu commands and lists the selected chart's annotations. |
| **Axis break** | Removes a value range from the scale of the whole axis (automatic, or a lower and an upper value from a dialog): columns reaching beyond it get a white gap with slanted lines and continue above it; labels keep the real values. |
| **Lane** | The strip one arrow occupies: above the plot for brackets, right of it for level differences. |
| **Pick mode** | After choosing an annotation command, the user clicks the columns it connects; the chart group is entered meanwhile. |
| **Core** | The pure-Python package `librecharts.core`; no UNO. |
| **Adapter** | The package `librecharts.lo`; the only place that talks to LibreOffice. |
