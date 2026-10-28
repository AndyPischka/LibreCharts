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
| **Difference arrow** | Annotation that shows the absolute or relative difference between two segments or columns. |
| **CAGR arrow** | Annotation that shows the compound annual growth rate between two columns. |
| **Axis break** | A gap in the value axis that shortens very tall columns. |
| **Core** | The pure-Python package `librecharts.core`; no UNO. |
| **Adapter** | The package `librecharts.lo`; the only place that talks to LibreOffice. |
