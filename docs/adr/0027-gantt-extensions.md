# 0027. Gantt extensions

- Status: accepted
- Date: 2026-11-04

## Context

M10 added the Gantt chart (ADR 0019) and deferred three features to M17: several bars per row,
working-day calendars with holidays, and import from CSV and project files. All three must keep the
existing pipeline: the data sheet is a view, the stored state is the truth, layout is a pure
function of the state (ADR 0007), `core/` has no UNO and no runtime dependencies, and every command
is one undo step.

## Decision

Taken from the M17 plan (removed after implementation).

### Several bars per row

- **Data sheet**: the existing columns keep their meaning (A label, B start, C end, D remark,
  E phase). Further start/end pairs follow in F/G, H/I, J/K, ...; pair `k >= 1` is
  `(2k+3, 2k+4)` (0-based). Existing sheets have only B/C and read exactly as before.
- **Row rules**: pair 0 follows the M10 rules (bar, milestone, phase, heading). Further pairs are
  bars: both dates are required, a single date is ignored, and start equal to end is a one-day bar.
  Milestones stay a row type of their own (pair 0); this avoids ambiguous side texts.
- **Model**: `Row.marks` holds the bars and milestones; `Row.start` / `Row.end` are the row's
  earliest start and latest end, so sorting and `starts()` keep working. A row with pair 0 as a
  milestone and further bars is a bar row.
- **Layout**: all marks of a row share the row's centre line; overlapping bars overlap. A phase
  bracket spans the row's earliest start to its latest end. The remark goes next to the last bar
  (the mark that ends latest), with the existing right/left/inside rule.
- **Data sheet view**: `lo/datasheet.py` gives every start/end column a date format, up to four
  pairs even before the user types them, so a new pair is read as a date.

### Working-day calendar

- **State**: `Calendar(working_days, holidays)` in `core/model.py`; `working_days` are Python
  weekdays (Monday = 0), `holidays` are single dates. `ChartState.calendar` defaults to every day
  working and no holidays, so existing charts stay linear. Schema 15.
- **Arithmetic** (`core/calendar.py`): `is_working`, `working_between` (whole weeks + remainder
  minus holidays, O(holidays)), `check_holidays` and `changed` for the dialog and the command.
- **Scale** (`core/timescale.py`): `fraction` counts working days; non-working days have no width.
  `day_width` is one working day or zero. The unit pair still follows calendar days, so hiding
  weekends does not change the number of months or weeks. `labelled` counts working days. A scale
  without any working day falls back to calendar days.
- **Layout**: bars run from the start of their first to the end of their last day; a bar with no
  working day keeps a fixed `MIN_BAR` width so it stays visible. Milestones and date lines on a
  non-working day sit on the boundary of the next working day.
- **UI**: a dialog with seven weekday checkboxes and a holidays field; the context menu and the
  sidebar also offer *All days* and *Monday to Friday* (keeping the holidays). The status line says
  *working days* while any day is hidden. The `WorkingDays` command takes
  `working=1,2,3,4,5&holidays=2026-12-25` for scripts and tests (ISO weekdays, 1 = Monday).

### Import

- **Core** (`core/gantt_import.py`, stdlib only): `parse_csv` reads the separator from the first
  line, maps a header with English or German names (else the data sheet's columns by position) and
  accepts ISO dates and datetimes, `30.6.2026`, slashes per language and Calc serials. Further bar
  pairs are read from *Start 2* / *End 2* headers or columns F/G, H/I, ...
- **Project files**: `parse_msppi` reads MSPDI XML directly or from a ProjectLibre `.pod` ZIP (the
  MSPDI document is embedded after Java serialization). Summary tasks become phases, milestones
  milestones, dated tasks bars, undated tasks headings; notes become the remark (first line, at
  most 80 characters); labels are indented by outline level. Nested summaries are flattened: each
  summary starts a phase.
- **Calendar**: `calendar_from_msppi` reads the base calendar's working weekdays and non-working
  exceptions; the import applies it when present.
- **State**: `state_from_table` fills `cells` and `values` (serials, phase markers, extra pairs),
  keeps the chart kind, format and calendar, and drops annotations and moved labels: they refer to
  the old rows.
- **Commands**: `ImportGanttCsv` and `ImportGanttProject` (context menu, sidebar, main menu), with
  `url=` for scripts and tests, else a file picker. A linked chart refuses the import: its source
  owns the data. One undo step through `chart.redraw`, then refresh an open data sheet.
- **Limits**: 20 MB decompressed, 5000 rows, ten bar pairs per row; larger files are rejected with
  a message.

## Alternatives considered

- **Several bars as consecutive rows with the same label**: fragile, and the label column would
  repeat; extra columns are language-neutral and keep existing sheets valid.
- **Per-row calendars**: one calendar per chart covers the common case; task calendars from
  ProjectLibre are ignored.
- **Binary `.mpp` files**: need a runtime dependency (MPXJ or similar), which ADR 0001 rules out.
  ProjectLibre exports MSPDI XML or saves `.pod`, which embeds it.
- **Keeping annotations and moved labels on import**: they refer to the old row indices; dropping
  them is safer than pointing them at unrelated new rows.
- **Importing into a linked chart**: the next link update would overwrite the imported data; the
  user must remove the link first.
- **An explicit "Type" column in CSV**: positions and header names are language-neutral enough.

## Consequences

- Charts with a calendar need schema 15; older charts migrate with the default calendar.
- Nested summaries lose their nesting in the phase colours (each summary starts a phase); the
  labels keep the outline indentation.
- A `.pod` written before ProjectLibre 1.5.5 has no embedded MSPDI and cannot be imported.
- Import is one-way; writing back to CSV or ProjectLibre is not planned.
- A bar that falls entirely on non-working days keeps a small fixed width instead of vanishing.
