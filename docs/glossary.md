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
| **Width row** | Optional Mekko data sheet row named "Width"/"Breite" right below the category names; sets column widths. |
| **Annotation** | An arrow or axis break the user placed on a chart; stored in the chart state by category index (ADR 0010). |
| **Difference arrow** | Annotation that shows the relative ("+25%") or absolute ("+5") difference between two columns, or two bars of one series. Drawn as a *bracket* above the columns or as a *level difference*. |
| **Level difference** | Difference arrow drawn right of the plot: dashed lines at the heights of both columns, a vertical arrow between them. |
| **CAGR arrow** | Annotation that shows the compound annual growth rate between two columns, over the years named by the categories (else the number of columns between them). |
| **Axis break** | Removes a value range from the scale of the whole axis (automatic, or a lower and an upper value from a dialog): columns reaching beyond it get a white gap with slanted lines and continue above it; labels keep the real values. |
| **Lane** | The strip one arrow occupies: above the plot for brackets, right of it for level differences. |
| **Pick mode** | After choosing an annotation command, the user clicks the columns it connects; the chart group is entered meanwhile. |
| **Core** | The pure-Python package `librecharts.core`; no UNO. |
| **Adapter** | The package `librecharts.lo`; the only place that talks to LibreOffice. |
