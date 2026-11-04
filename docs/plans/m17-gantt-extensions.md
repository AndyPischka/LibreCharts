# M17: Gantt extensions

Status: **agreed** (2026-11-04); delete this file after implementation and move the lasting
decisions into ADR 0027.

## Goal

Add the three Gantt features deferred from M10 (ADR 0019):

1. **Several bars per row** - one activity can have more than one bar.
2. **Working-day calendar** - weekends and holidays can be hidden from the time scale.
3. **Import** - fill the data sheet from a CSV file or a ProjectLibre project.

All three keep the existing invariants: `core/` has no UNO and no runtime dependencies, layout is a
pure function of the state (ADR 0007), every command is one undo step, and the stored state stays
readable through a schema migration.

## Non-goals

- Per-row calendars. One calendar per chart; ProjectLibre task calendars are ignored.
- Task dependencies (predecessors), resources, costs and progress. Import reads names and dates only.
- Writing back to CSV or ProjectLibre. Import is one-way.
- Editing the calendar in the data sheet. It is a chart setting, like the colour scheme.
- Binary `.mpp` files. ProjectLibre's `.pod` (which embeds MSPDI XML) and MSPDI `.xml` only.
- Working-day durations in labels. The calendar only changes the x mapping; a bar still runs from
  its start date to its end date.

## Part A: several bars per row

### Data sheet

Keep the existing columns and append bar pairs:

| A | B | C | D | E | F | G | H | I | J | K | ... |
|---|---|---|---|---|---|---|---|---|---|---|---|
| label | start | end | remark | phase | start 2 | end 2 | start 3 | end 3 | start 4 | end 4 | ... |

- Pair 0 is `(B, C)`; pair `k >= 1` is `(2k+3, 2k+4)` (0-based column indices).
- Existing sheets have only pair 0 and read exactly as before.
- The header row names the extra pairs `Start` / `End` again.
- `core/gantt.py` exposes `pairs(width)` so `lo/datasheet.py` can give every start/end column the
  date format.

### Model (`core/gantt.py`)

- New `Mark(start, end, kind)` with `kind` `"bar"` or `"milestone"`.
- `Row` gets `marks: tuple[Mark, ...]`; `Row.start` / `Row.end` stay the row's overall extent
  (earliest start, latest end) so sorting, the scale and `starts()` keep working.
- Pair 0 follows the existing rules: two dates a bar (equal dates a milestone), one date a
  milestone, no dates a heading, phase marker a phase.
- Extra pairs are **bars**: both dates required, `start == end` is a one-day bar, a single date is
  ignored. Milestones stay a row type of their own (pair 0); this avoids ambiguous side texts.
- Swapped dates are put in order per pair.
- `Row.kind`: `"phase"` if the marker is set; `"heading"` if there are no marks; `"milestone"` if
  pair 0 is a milestone and there are no extra bars; else `"bar"`.
- Colour: the phase above, as today.
- Sorting by start date and `starts()` use the earliest start of the row.

### Layout (`core/layout/gantt.py`)

- All marks of a row share the row's band and centre line. Overlapping bars overlap; the row height
  stays one slot (no sub-lanes).
- A phase bracket spans from the row's earliest start to its latest end.
- The remark goes next to the **last bar** (the mark that ends latest), using the existing
  right/left/inside rule. A milestone-only row keeps its date as the side text, plus the remark.
- A bar that contains no working day (only possible with a calendar) gets a fixed minimum width so
  it stays visible.
- The primitive structure still depends on the data only, never on the size.

### Sample and tests

- The sample gets one row with two bars (for example *Testing* split into two periods).
- Core tests: pair parsing, row kinds, sorting by earliest start, one rectangle per bar, remark
  placement, structure independent of size.
- `tests/lo`: insert, edit an extra pair in the data sheet, reload ODP and PPTX.

## Part B: working-day calendar

### Model

`Calendar` joins `Format` and `Link` in `core/model.py`:

```python
@dataclass(frozen=True, slots=True)
class Calendar:
    working_days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)  # Monday = 0
    holidays: tuple[date, ...] = ()
```

- Normalised in `__post_init__`: sorted, unique, at least one working day, weekdays `0..6`.
- `ChartState.calendar: Calendar = Calendar()`.
- Schema 15: migration `_v14_to_v15` adds the default (all days, no holidays), so existing charts
  render exactly as before.
- `state_io` writes holidays as ISO dates and reads them back; malformed input is a `StateError`.

### Arithmetic (`core/calendar.py`)

- `is_working(day)`: weekday in `working_days` and not a holiday.
- `working_between(start, end)`: working days in `[start, end)` as full weeks + remainder minus
  holidays; O(number of holidays), so decades-long scales stay cheap.
- `check_holidays(text, language)`: parse the dialog's lines (newline, comma or semicolon
  separated) with the date rules of `value_line.check_date`; returns the sorted dates or an error
  key.
- `from_query(query, language)`: `working=1,2,3,4,5&holidays=2026-12-25,...` for scripts and tests.

### Scale and layout

- `time_scale(first, last, calendar)`; `TimeScale` carries the calendar.
- `TimeScale.fraction(day)` counts working days from the scale start, clamped to `[0, 1]`.
- New `TimeScale.working_days` and `TimeScale.day_width(day)` (0 on a non-working day).
- If the scale contains no working day at all, fall back to calendar days so the chart still draws.
- `periods`, `years` and the unit choice stay calendar-based (a month is a month); `labelled` counts
  working days when a calendar is active, so a heavily cut period stays unlabelled.
- `core/layout/gantt.py`: bars from `x(start)` to `x(end + 1 day)`, milestone centre
  `x(day) + day_width(day) / 2`, date lines at `x(day)`; header, shading and gridlines use the same
  `x`, so month and week widths vary with their working days.
- A bar with no working day gets a fixed `MIN_BAR` (1/100 mm) so it stays visible.

### UI

- New `lo/calendardialog.py`, built in code like the axis-break dialog and opened asynchronously:
  seven weekday checkboxes and a multiline holidays field; validation in `core/calendar.py`.
- Command `WorkingDays`:
  - no query: show the dialog;
  - with `working=...&holidays=...`: apply directly (scripts and `tests/lo`).
- Quick options in the context menu's *Working days* submenu and in the sidebar's options section:
  *All days* (`ChangeChart?working=all`, working days Monday..Sunday) and *Monday to Friday*
  (`ChangeChart?working=weekdays`); both keep the holiday list. *Custom...* / *Working days...*
  opens the dialog.
- The status line says *Gantt chart, 9 rows, working days* / *Gantt-Diagramm, 9 Zeilen,
  Arbeitstage* while any day is non-working (fewer than seven working weekdays or holidays).
- New messages in English and German.

### Tests

- `core/calendar.py`: weekends, holidays on working and non-working days, leap years, ranges,
  validation, query parsing.
- `core/timescale.py`: fractions and widths with a calendar; the unit choice does not change.
- `core/layout/gantt.py`: bars across weekends, a milestone on a weekend, a date line on a weekend,
  a bar with no working day, structure independent of size.
- `tests/lo`: set a calendar through `WorkingDays?working=...`, reload; the dialog itself is tested
  by hand (headless limitation, like the axis-break dialog).

## Part C: import from CSV and ProjectLibre

### Core (`core/gantt_import.py`, stdlib only)

- `parse_csv(text, language) -> Table`:
  - separator from the first line (comma, semicolon, tab), quoted fields, UTF-8 BOM;
  - header mapping case-insensitively by aliases (English and German: *Activity/Task/Name/Aufgabe*,
    *Start/Beginn*, *End/Finish/Ende*, *Remark/Note/Notes/Bemerkung*, *Phase*), else columns A..E by
    position;
  - dates: ISO date or datetime, `30.6.2026`, `6/30/2026` in English, `30/6/2026` otherwise, and
    bare Calc serial numbers; a header row is detected and skipped.
- `parse_msppi(data: bytes) -> Table`:
  - plain MSPDI XML, or a ProjectLibre `.pod` ZIP that contains an MSPDI entry (scan the entries
    for `<Project` and parse from there);
  - `xml.etree.ElementTree`, namespace-agnostic tag matching;
  - tasks: `Name`, `Start`, `Finish`, `Milestone`, `Summary`, `Notes`, `Active`, `OutlineLevel`;
    skip UID/ID 0 and inactive tasks; summary tasks become phase rows, milestones milestones, dated
    tasks bars, undated tasks headings; nested summaries are flattened (each summary starts a
    phase); labels are indented by outline level;
  - limits on rows and decompressed size, with message keys.
- `calendar_from_msppi(data) -> Calendar | None`: the base calendar's working weekdays and its
  non-working exceptions (holidays), if the file has one.
- `state_from_table(table, base: ChartState) -> ChartState`: fills `cells` / `values` with serials,
  phase markers and extra bar pairs; keeps the chart kind and format; **drops annotations and moved
  labels** (they refer to the old rows).

### Adapter and UI

- `lo/commands.py`: `import_gantt_csv` and `import_gantt_project`, with `url=` for scripts and
  tests, else a file picker (`.csv/.txt/.tsv`, `.pod/.xml`). One undo step through `chart.redraw`,
  then refresh an open data sheet.
- A linked chart refuses the import with *Remove the data link first*: its source owns the data.
- `extension/entry.py`: dispatch `ImportGanttCsv` and `ImportGanttProject`.
- Context menu entries *Import from CSV...* and *Import from ProjectLibre...*; two sidebar buttons;
  entries in the main LibreCharts menu; new messages in English and German.
- New icons `import_csv_16/26.png` and `import_project_16/26.png` (or reuse existing icons for the
  first cut).

### Tests

- Core: CSV with header and without, all separators, quoted fields, every date format, invalid
  rows; a minimal MSPDI XML with summary, milestone, bar and heading; a `.pod` ZIP with an embedded
  MSPDI; calendar extraction; size limits.
- `tests/lo`: dispatch `ImportGanttCsv?url=...` and `ImportGanttProject?url=...` with temporary
  files; assert cells, values, one undo step, the open data sheet, and reload as ODP and PPTX.

## Schema and persistence

- `SCHEMA_VERSION` 15; `_v14_to_v15` adds `calendar` (all days, no holidays).
- Multi-bar data and imports need no new field: they fill the existing grid.
- ODP and PPTX persistence are unchanged; older LibreCharts rejects schema 15 with its usual
  "saved by a newer LibreCharts" message.

## Order of work

1. **Part A** - data model and layout; no schema change, smallest step.
2. **Part B** - calendar, schema 15, dialog.
3. **Part C** - import, which uses A (extra pairs) and B (calendar).

Each part is its own commit (or PR) with `uv run poe check` green; parts B and C also run
`uv run poe test-lo`.

## Docs

- New ADR 0027 *Gantt extensions* with the lasting decisions.
- Glossary: *Bar pair*, *Working calendar*, *Holiday*.
- `ARCHITECTURE.md`: `core/calendar.py`, `core/gantt_import.py`, `lo/calendardialog.py`; update the
  `core/gantt.py` and `layout/gantt.py` rows.
- `CHANGELOG.md` under *Unreleased / Added*.
- `ROADMAP.md`: M17 done when merged.
- `README.md`: the Gantt paragraph.

## Decisions (2026-11-04)

1. **Remark of a multi-bar row**: next to the last bar.
2. **Calendar UI**: the dialog plus the quick *All days* / *Monday to Friday* options.
3. **Import scope**: CSV + MSPDI `.xml` + ProjectLibre `.pod`.
4. **Import into a linked chart**: refuse; the source owns the data.
5. **Annotations and moved labels on import**: drop.
