# 0019. Gantt chart

- Status: accepted
- Date: 2026-10-29

## Context

M10 adds a project timeline as in think-cell: one row per activity with a bar from start to end
date, milestones, phases over several rows and a date scale with two levels. It must use the
existing pipeline (Calc data sheet, `ChartState`, pure layout, native shapes, format, colour
schemes, resize, undo, ODP/PPTX), and the layout must stay a pure function of the state
(ADR 0007), so nothing in it may depend on today's date.

## Decision

Taken from the M10 plan (removed after implementation), with the recommended answers to its open
questions:

- **Chart kind**: `ChartKind` gets `"gantt"`; `grouping` stays `"stacked"` without meaning. No new
  state field. Schema 10, whose migration from 9 changes nothing, so that an older LibreCharts
  rejects Gantt charts with its "saved by a newer LibreCharts" message.
- **Data sheet by position** (`core/gantt.py`), like the scatter sheet (ADR 0018): A label, B start,
  C end, D remark, E phase marker; the header row only names the columns. The row type follows from
  the cells: start and end give a bar, one date (or start equal to end) a milestone, any text in E
  with dates a phase, no dates a heading; empty rows are skipped. Swapped dates are put in order. A
  "Type" column with words in two languages was rejected: positions are language-neutral.
- **Dates are Calc serial numbers** (days since 1899-12-30, Calc's default null date), which
  `getDataArray` returns as floats, so formulas such as `=B2+14` work. Times of day are ignored;
  years outside 1000..9000 count as empty. Calc's serials have no 29 February 1900, unlike Excel's.
  The data sheet shows columns B and C in the standard date format of the Calc document's locale
  (the locale it also parses typed dates in), set on the whole columns so new rows get it too.
- **Time scale** (`core/timescale.py`): chosen automatically from the date range only, the finest of
  the pairs days/months, weeks/months, months/years, quarters/years, years/decades whose lower level
  has at most 40 units. The scale snaps to whole lower units (weeks start on Monday); an upper unit
  cut to less than half its length stays unlabelled. Week numbers are plain ISO numbers: "KW 27" does
  not fit a narrow week, and the upper level names the month. There is no user override in M10.
- **Layout** (`core/layout/gantt.py`): label column (width from the longest label, at most 35 % of the
  chart), the two-level header, one band per row. Bars span from the start of their first to the end
  of their last day. Milestones are `Polygon` diamonds of fixed size (they stay small on resize, like
  markers) labelled with their date; the year is shown only when the scale spans several years.
  A phase is a thin bar in its colour with a tick down at both ends, and its label is bold, like a
  heading's (new text role `heading`). A remark goes right of the mark, left of it when the mark ends
  in the last quarter of the scale, or inside a bar that spans nearly all of it: decided from the
  dates, not the size. Every other upper unit is shaded (new `Rect` colour `SHADE`, a light mix of
  the scheme's line colour into its background).
- **Colours per phase**: phases are numbered from 0 in order; bars and milestones take the number of
  the phase above them (rows before the first phase use 0). `ChartState.colors` indexes phases.
- **Date lines are value lines** (ADR 0014) whose value is a serial number: a dashed vertical line
  with its date below the rows. A date line outside the rows extends the scale. The value-line dialog
  asks for a date on Gantt charts, parsed in the chart's language (ISO always, `30.6.2026` always,
  slashes month-first in English and day-first otherwise).
- **No automatic today line**: "Add today line" (`TodayLine` command) adds a date line with today's
  date once. Recomputing it when the document opens was rejected: the document-open job would change
  the chart and mark the document as modified, and the layout would depend on the clock.
- **Options and format**: sorting by start date (`sort="ascending"`; `"descending"` is rejected)
  sorts the rows between phases and headings and keeps those in place. Gridlines (lower units) are
  optional and off for a new chart; axis, series names, markers and the number format do not apply.
  Same scale and the other annotations do not apply either.
- **UI**: `InsertGanttChart` in menu, toolbar and sidebar with 16 px and 26 px icons; the context
  menu has "Add date line...", "Add today line" and "Sort categories" with "By start date"; the
  sidebar adds a today-line button; the status line says "Gantt chart, 9 rows" / "Gantt-Diagramm,
  9 Zeilen".

## Alternatives considered

- **A user-selectable scale unit**: needs a state field and UI; the automatic choice covers the
  common ranges. Can come later without a migration of existing charts.
- **Phases as brackets of lines only**, as first planned: lines carry no series colour, so the link
  between a phase and its bars would be lost.
- **"KW"/"W" prefixes on week numbers**: did not fit 26 weeks in a chart of 60 % slide width.
- **Several bars per row, working-day calendars, import from project files**: deferred to M17.

## Consequences

- Charts of the new kind need schema 10; older charts load unchanged.
- The milestone date and remark texts are estimated, not measured: very long remarks can leave the
  chart; label placement (M13) addresses that.
- A document with a changed null date (Calc option "1904" or "1900-01-01") is not supported: the
  data sheet is always a new Calc document with the default null date.
