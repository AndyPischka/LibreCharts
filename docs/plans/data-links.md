# Plan: M11 data links to Calc and Excel files

Status: draft, not yet agreed (2026-10-29).

## Goal

A chart can take its data from a range in an external spreadsheet (`.ods`, `.xlsx`, `.xls`,
`.csv`) instead of its own data sheet, and is updated on demand, as with think-cell's Excel data
links. A monthly report deck can then be refreshed from the new workbook in one step.

Non-goals: live updates while the source is edited, links to databases or web sources, writing
back to the source, links between charts in different presentations.

## Approach

### State (`core/model.py`, `core/state_io.py`, new `core/links.py`)

- `ChartState.link: Link | None = None` with
  - `url`: the source file, stored **relative to the presentation** when both are on the same
    drive (so a folder with deck and workbook can be moved), else absolute,
  - `sheet`: sheet name, `range`: an address (`B2:F6`) or a named range of the file,
  - `updated`: ISO timestamp of the last successful update (display only, never used by layout).
- The fetched data is stored in `cells`/`values` as today, so the chart draws, copies and
  exports without the source. Linked cells hold the **values** of the source, not its formulas
  (they refer to the source's own sheets).
- `core/links.py`: parse and validate addresses and range names, resolve relative URLs (pure
  string work on `file:///` URLs), compare old and new data to report "changed / unchanged",
  and the range shape rules: the chart takes the range as its whole data sheet (first row and
  column = names, as everywhere).
- Schema version 11; migration adds `"link": null`.

### Updating (`lo/links.py`)

- Open the source with `loadComponentFromURL` **hidden, read-only, macros never**
  (`MacroExecutionMode = NEVER`), read the range with `getFormulaArray`/`getDataArray`, close it.
  An already open source document is used as it is (unsaved edits included) and left open.
- Write the new state through `chart.redraw`: one undo step per chart; "Update all links" updates
  every linked chart of the presentation in **one** undo action and opens each source file once.
  Same-scale groups (M8) are re-laid out with them.
- Errors (file missing, sheet or range gone, password protected) leave the chart unchanged and
  are collected into one message listing the charts concerned.

### Data sheet of a linked chart

- "Edit chart data" opens the data sheet read-only with an info line ("Linked to
  Sales.xlsx, Sheet1!B2:F6") and the commands "Open source" and "Remove link". Editing it
  would be overwritten by the next update, so it is not offered.

### Creating a link

- From Impress: "Link data..." on a selected chart opens a dialog (`lo/linkdialog.py`, built like
  `lo/axisdialog.py`): file picker, sheet list read from the file, range field. Validation in
  `core/links.py`; the dialog itself is tested by hand.
- From Calc (open question 1): with a range selected in Calc, "LibreCharts -> Link to selected
  chart" in Calc's menu links that range to the chart selected in the last active presentation.

### On opening a presentation

- The existing document-open job checks the linked charts' sources' modification times
  (`SimpleFileAccess.getDateTimeModified`) and, if any is newer than `updated`, shows an info bar
  ("Linked data has changed. Update now?") instead of a modal dialog. It does not update by
  itself, so opening a deck never modifies it.

### UI

- Context menu and sidebar of a linked chart: "Update link", "Open source", "Remove link"; of an
  unlinked one: "Link data...". Presentation level (menu, sidebar): "Update all links".
- The sidebar status shows the source and the time of the last update.

## Affected modules

`core/model.py`, `core/state_io.py`, new `core/links.py`, `core/menu.py`, `core/panel.py`,
`core/messages.py`, new `lo/links.py`, new `lo/linkdialog.py`, `lo/datasheet.py` (read-only mode),
`lo/chart.py`, `lo/samescale.py`, `lo/commands.py`, `lo/sidebar.py`, the document-open job,
`extension/entry.py`, `extension/Addons.xcu` (Calc menu entry if agreed).

## Tests

- `tests/core`: migration v10 -> v11; address and range-name validation; relative/absolute URL
  resolution incl. Windows drive letters and different drives; change detection; range shape.
- `tests/lo/test_links.py`: a fixture workbook (`.ods` and `.xlsx`, written by the test into a
  temp dir) -> link, update after changing the file, one `.uno:Undo` restores; update all with two
  charts in one undo step; missing file leaves the chart unchanged; moving deck and workbook
  together keeps the link; ODP and PPTX reload keep the link (PPTX: check the custom property).
  The info bar and the dialog are tested by hand.

## Docs

New ADR "Data links" (values not formulas, relative URLs, no automatic updates, security of
opening the source); ARCHITECTURE.md (`links.py`, `linkdialog.py`); glossary ("Data link",
"Source", "Update"); CHANGELOG; ROADMAP; README; SECURITY.md (files opened by the extension).

## Open questions (recommendation first)

1. Link creation from Impress only in M11 (recommended) or also a command in Calc's menu (better
   workflow, but the first LibreCharts UI outside Impress; the non-goal "Writer, Calc or Draw
   support" is about charts there, not about this helper).
2. Linked charts: data sheet read-only (recommended) or editable with a warning that the next
   update overwrites edits.
3. Store values (recommended) or formulas of the source range.
4. Check for changed sources when opening: info bar (recommended), modal question, or nothing.
5. A range that grows in the source (new month): only through named ranges (recommended) or
   also by detecting the used area next to the linked range.
