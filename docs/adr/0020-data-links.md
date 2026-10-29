# 0020. Data links

- Status: accepted
- Date: 2026-10-29

## Context

M11 lets a chart take its data from a range of an external spreadsheet (`.ods`, `.xlsx`, `.xls`,
`.csv`) instead of its own data sheet, updated on demand, as with think-cell's Excel data links: a
monthly report deck is refreshed from the new workbook in one step. Live updates while the source
is edited, databases and web sources, writing back to the source and links between presentations
are out of scope. The chart state stays the truth (ADR 0003, 0005), every operation stays one undo
step, and opening a presentation must never change it.

## Decision

Taken from the M11 plan (removed after implementation), with the recommended answers to its open
questions:

- **State**: `ChartState.link: Link | None` (schema 11; the migration from 10 adds `"link": null`).
  A `Link` holds the source's absolute `url`, its URL `relative` to the presentation, `sheet` and
  `range` (an address such as `B2:F6`; an empty sheet makes `range` the name of a named range),
  `updated` (local time of the last update, display only) and `modified` (the source's modification
  time read at that update). The layout never reads the link.
- **Values, not formulas**: the fetched data is stored in `cells` and `values` like data sheet data,
  so a linked chart draws, copies and exports (ODP, PPTX) without its source. The source's formulas
  refer to its own sheets and are not kept. The names in the first row and column are stored as the
  source displays them (a date header stays "Jan 2026"); every other cell keeps its number.
- **The range is the whole data sheet**: first row and column are names, as in every data sheet; at
  least 2 x 2 cells, at most 10,000. Typed or pasted ranges are accepted in Calc (`$Sheet1.$B$2:$F$6`)
  and Excel (`Sheet1!B2:F6`) notation. A range that grows in the source (a new month) is followed
  through a **named range** only; guessing the used area next to a linked range was rejected as
  surprising.
- **Relative and absolute URL**: both are stored; an update looks next to the presentation first
  (deck and workbook moved together), then at the absolute URL (the deck was saved elsewhere).
  Relative URLs exist only for `file:` URLs on the same drive or UNC share; an unsaved presentation
  gets one on the first update after it is saved. Every successful update rewrites both.
- **Reading the source** (`lo/links.py`): hidden, read-only, `MacroExecutionMode` NEVER_EXECUTE and
  `UpdateDocMode` NO_UPDATE (the source's own links keep their cached values), closed afterwards. A
  source the user already has open is read as it is, unsaved edits included, and left open. CSV files
  are split at the separator found most often in their first line (comma, semicolon or tab).
- **Updating**: "Update link" updates the selected linked charts, "Update all links" every linked
  chart of the presentation; each source is opened once per update. Charts with new data are redrawn
  through `chart.apply_changes`: one undo step for all of them, same-scale groups included. A chart
  whose data did not change only gets its new times stored, without an undo step or redraw.
  Problems (file missing, sheet or range gone, password protected, range too small or too large)
  leave the chart unchanged and are collected into one message naming the slides.
- **Data sheet of a linked chart**: opened as a protected, read-only view ("Show chart data") whose
  title names the source; its edits would be overwritten by the next update. A visible data sheet
  shows an info bar with "Open source" and "Remove link". Linking, updating and unlinking refresh an
  open data sheet in place; "Remove link" makes it editable again with the last fetched values.
- **Creating a link** only from Impress: "Link data..." (context menu, sidebar, LibreCharts menu)
  opens a dialog (`lo/linkdialog.py`) with a file picker, the file's sheets and named ranges, and the
  used area of the chosen sheet as a proposal. OK reads the range first and keeps the dialog open
  with the reason if that fails, so no link is made that cannot be read. "Change link..." is the same
  dialog on a linked chart. Scripts and tests pass `LinkData?url=...&sheet=...&range=...` instead.
- **On opening a presentation** the document-open job compares the sources' modification times
  with `modified` (equality only, so time zones do not matter) and shows an info bar "Linked data of
  this presentation has changed" with "Update now". It never updates by itself, so opening a deck
  never modifies it. The check opens no source.

## Alternatives considered

- **A command in Calc's menu** ("Link to selected chart"): a better workflow, but the first
  LibreCharts UI outside Impress. Can come later.
- **An editable data sheet with a warning**: edits would silently vanish with the next update.
- **Storing the source's formulas**: they refer to sheets the presentation does not have.
- **A modal question when opening**, or no check at all: a modal dialog interrupts every opening of
  the deck; no check hides stale numbers. The info bar informs without blocking.
- **Only a relative or only an absolute URL**: either breaks one of the two common moves (the folder
  with deck and workbook, or the deck alone).
- **Comparing the modification time with the update time**: mixes two clocks and time zones.

## Consequences

- Charts need schema 11 for a link; older charts load unchanged, and an older LibreCharts rejects a
  linked chart with its "saved by a newer LibreCharts" message.
- Opening a source runs Calc's import filters on a file of the user's choice, but never its macros;
  passwords are not asked for (such sources report "cannot be opened").
- A source whose null date is not 1899-12-30 (Calc option "1904") shifts Gantt dates, as in the data
  sheet (ADR 0019).
- Sheet-local named ranges are not found; only document-wide names are.
