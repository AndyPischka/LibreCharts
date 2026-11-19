# 0030. Accessibility and export

- Status: accepted
- Date: 2026-11-19

## Context

A LibreCharts chart is a group of native shapes. Screen readers and the PDF export see a group
without a name, colour is the only thing that tells series apart, and the data can only leave the
chart through the data sheet window. M20 asks for alternative text generated from the chart data,
patterns as well as colours for colour-blind readers, and exporting the chart data as CSV.

## Decision

- **Alternative text**: every chart group gets a `Title` (the chart type, e.g. *Column chart
  (100 %)*) and a `Description` that lists the data in reading order: a summary sentence, then
  one sentence per series (`Product A: 2023 = 10, 2024 = 12.`), per waterfall step, scatter point
  or Gantt row. Numbers use the chart's format (decimals, magnitude, unit, separator) and the
  chart's language, like its labels. `core/alttext.py` builds the text; `render.describe` writes it
  on insert and on every redraw (data edits, links, options), only when it changed. Descriptions
  longer than 4000 characters are cut with an ellipsis.
- **Patterns**: a per-chart format option `patterns` (schema 16, `false` for existing charts),
  switched in the *Format* menu and copied with *Copy chart format*. Series fills (columns, bars,
  areas, Mekko and pie segments, bubbles, legend swatches) get a hatch over their colour; line
  series get a dash pattern. The pattern is chosen by series index (`style.HATCHES`,
  `style.DASHES`), so neighbouring series never share one; the first series stays plain. Hatch
  lines are drawn half way between the fill and its readable text colour, so labels stay legible.
- **CSV export**: `org.librecharts:ExportCsv` (context menu, sidebar, menu) writes the data sheet of
  the selected chart: every cell, the evaluated value of a number (a formula exports its result)
  and the text of anything else. The dialect follows the chart's decimal separator, as spreadsheets
  expect: a decimal point with commas between fields, a decimal comma with semicolons. Numbers are
  written without loss and without exponents; Gantt date columns are ISO dates. The file is UTF-8
  with a byte order mark and CRLF line ends. `url=<url>` skips the file picker. It changes nothing
  in the presentation, so there is no undo step.

## Alternatives considered

- **Alternative text only on request**: authors forget; generated text that follows the data is
  what makes a deck accessible by default.
- **Alternative text on every child shape**: screen readers would read dozens of bars and labels;
  the group is the object a reader cares about.
- **A document-wide pattern switch**: decks mix charts for print (patterns) and screen (colour);
  a format option also travels with *Copy chart format*.
- **Patterns by palette index**: two series with the same colour override would share a pattern
  too, which defeats the purpose.
- **Excel (`.xlsx`) export**: needs a writer we would have to bundle (ADR 0001); CSV opens
  everywhere and the data sheet window already offers Calc's own *Save as*.

## Consequences

- Schema 16 documents cannot be read by older builds; their shapes still display.
- LibreOffice's PPTX filter drops the alternative text of groups. ODP keeps it; a chart from a PPTX
  file gets its text back with its next redraw (any data or option change).
- Hatches enlarge PDFs slightly and print well in black and white. A chart's labels on a hatched
  fill keep the black/white contrast rule of ADR 0014.
- The alternative text is regenerated on every redraw: a text the author typed by hand into the
  shape's *Description* is replaced. That is the price of text that always matches the data.
