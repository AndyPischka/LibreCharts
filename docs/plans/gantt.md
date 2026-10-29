# Plan: M10 Gantt chart / timeline

Status: draft, not yet agreed (2026-10-29). Builds on M9 (data sheet with fixed columns).

## Goal

A project timeline as in think-cell: one row per activity with a bar from start to end date,
milestones as diamonds, phases as brackets over several rows, a date scale with two levels
(e.g. years over months) and labels per row. Data comes from the Calc data sheet like every other
chart, so dates can be calculated with formulas.

Non-goals: dependencies between activities, critical path, resource planning, import from
project files (MS Project, ProjectLibre), working-day calendars and holidays.

## Approach

### State (`core/model.py`, `core/state_io.py`)

- `ChartKind` gets `"gantt"`; `grouping` stays `"stacked"` without meaning.
- No new chart field: the scale unit is derived from the date range (below), date lines are value
  lines (M6) whose `value` is a date serial number.
- Schema version 10 for the new kind (ADR 0015 rule).

### Data sheet (`core/gantt.py`, `lo/datasheet.py`)

- One row per activity, columns by position like the scatter sheet (M9): A label, B start,
  C end, D remark (optional text right of the bar), E phase marker (optional, like the waterfall's
  "Total" marker: any text marks the row as a phase). The header row only names the columns.
- Dates are Calc serial numbers (days since 1899-12-30), which `getDataArray` already returns as
  floats. `core/gantt.py` converts them with `datetime.date.fromordinal` (no dependency).
- Row type: start and end -> bar; start only (or start == end) -> milestone; phase marker ->
  phase bracket from start to end; no dates -> a heading row (label only, bold).
- `lo/datasheet.py` sets a date number format on columns B and C when it writes a Gantt sheet,
  so the user sees dates, not serial numbers. Today it writes cells without formats; the format
  is chosen through `XNumberFormatsSupplier` with the UI locale.

### Layout (`core/layout/gantt.py`, `core/timescale.py`)

- New `core/timescale.py`: from the date range, pick the unit pair (days over months, weeks over
  months, months over years, quarters over years) so that the lower level has 6..40 units. It
  depends on the data only, never on the size (ADR 0007). Month names and the "Q" / "KW" style
  come from `core/messages.py` in `Format.language`.
- Layout: label column left (width from the longest label, capped at 35 % of the chart), the
  two-level scale header on top, one row band per data row below. Bars are `Rect`s (series 0, or
  the colour of their phase), milestones `Polygon` diamonds of fixed size, phases a bracket from
  `Line`s with the label bold. The remark sits right of the bar; when it would leave the chart it
  goes left of the bar instead (decided per row from the dates, so still data-only).
- Gridlines (`Format.gridlines`) at the lower-level unit boundaries, alternating shading per
  upper-level unit as `Rect`s behind the bars (always emitted, maybe transparent: same structure).
- Date lines: value lines (M6) with a date value draw a vertical dashed line with the date as
  label; the value-line dialog accepts a date for Gantt charts (`core/value_line.py` parses it in
  the chart's language). There is no automatic "today" line, because the layout must stay a pure
  function of the state; "Add today line" fills in today's date once.

### Options, format and annotations

- Format: series names, magnitude and unit do not apply; `decimals` neither. Gridlines yes.
- Sorting (M5): "by start date" as an option for Gantt charts (`sort=ascending` keyed by start).
- Annotations: value lines only. Same scale (M8): no.
- Colour schemes (M8) apply; series colours: per phase (index = phase number).

### UI

- `InsertGanttChart` in menu, toolbar, sidebar, `entry.py`, with icons and sample data (a
  project with two phases, five activities and two milestones over half a year).
- Context menu: "Add date line..." (value line dialog), "Add today line", "Sort by start date".
- Status line: "Gantt chart (12 rows)" / "Gantt-Diagramm (12 Zeilen)".

## Affected modules

`core/model.py`, `core/state_io.py`, new `core/gantt.py`, new `core/timescale.py`, new
`core/layout/gantt.py`, `core/layout/chart.py`, `core/datasheet.py` (sample), `core/value_line.py`
(dates), `core/sorting.py`, `core/format.py` (supported options), `core/menu.py`,
`core/panel.py`, `core/messages.py` (month names, units), `lo/datasheet.py` (date formats),
`lo/formatdialog.py` (date input), `lo/chart.py`, `lo/commands.py`, `extension/entry.py`,
`extension/Addons.xcu`, `extension/images/`.

## Tests

- `tests/core`: migration v9 -> v10; row types from the sheet (bar, milestone, phase, heading,
  formulas giving dates); serial number <-> date incl. the 1900 leap-year quirk boundary; unit
  pair per range length; month and quarter labels in English and German; remark left or right;
  date line parsing in both languages; sort by start; structure independent of size.
- `tests/lo/test_gantt.py`: insert, data sheet shows dates (number format of B and C), editing a
  date moves the bar, resize, date line with one undo, ODP and PPTX reload.

## Docs

New ADR "Gantt chart" (data sheet columns, scale units, no automatic today line);
ARCHITECTURE.md (`gantt.py`, `timescale.py`, layout); glossary ("Gantt chart", "Activity",
"Milestone", "Phase", "Date line", "Time scale"); CHANGELOG; ROADMAP; README.

## Open questions (recommendation first)

1. Data sheet by position with an optional phase marker column (recommended) or a "Type" column
   with words ("Bar", "Milestone", "Phase" in two languages).
2. Today line set once by a command (recommended) or recomputed when the document opens (the
   document-open job would then change the chart, which marks the document as modified).
3. Scale unit chosen automatically only (recommended for M10) or also selectable by the user.
4. Milestones with a label of their date next to the diamond: on (recommended) or off.
5. Several bars in one row (e.g. interrupted activities): later (recommended) or in M10.
