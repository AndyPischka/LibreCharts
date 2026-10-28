# Glossary

Use these terms consistently in code, UI strings and docs.

| Term | Meaning |
|---|---|
| **Chart** | One LibreCharts object on a slide: a group of shapes plus its data. |
| **Chart state** | The persisted description of a chart: raw data sheet cells (incl. formulas), their evaluated values, chart kind, grouping and a schema version. Stored as JSON in the document. |
| **Primitive** | A rectangle, line or text box produced by layout; plain geometry in 1/100 mm that the adapter turns into a shape. |
| **Data sheet** | The Calc document in which the user edits a chart's values (ADR 0003). |
| **Category** | One position on the category axis (x-axis of a column chart). |
| **Series** | One set of values across categories; one colour, one legend entry. |
| **Segment** | One rectangle: the value of one series in one category. |
| **Total label** | The label above a stacked column showing the sum of its segments. |
| **Waterfall** | Bridge chart: floating segments show increases and decreases between a start and an end value. |
| **Subtotal** | A waterfall column that shows the running total instead of a change. |
| **Marimekko (Mekko)** | Stacked chart whose column width is also data (e.g. market size); segments are usually in percent. |
| **Difference arrow** | Annotation that shows the absolute or relative difference between two segments or columns. |
| **CAGR arrow** | Annotation that shows the compound annual growth rate between two columns. |
| **Axis break** | A gap in the value axis that shortens very tall columns. |
| **Core** | The pure-Python package `librecharts.core`; no UNO. |
| **Adapter** | The package `librecharts.lo`; the only place that talks to LibreOffice. |
