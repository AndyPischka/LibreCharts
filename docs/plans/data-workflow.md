# M28: Data workflow

- Status: proposed
- Milestone: M28 (7.0)
- Builds on: M11 data links (ADR 0020), M17 Gantt import, M18 deck specification (ADR 0028)
- Decision: no new ADR for the import itself; an ADR for the shared-source model and the
  auto-update setting

## Goal

Getting data into a chart is still a manual copy/paste into the Calc window. M28 closes the three
common paths: a file with a table, a range copied from another spreadsheet, and a link that should
refresh itself when the deck opens. It also gives several charts one source instead of making the
user repeat the same link.

## Scope

### Import a file into any data sheet

- *Import data...* in the chart context menu, the sidebar and the *Data* menu: choose a CSV, ODS,
  XLSX or XLS file, a sheet and a range, read it, and write it into the chart's data sheet.
- This reuses the link dialog's file/sheet/range browser and `lo/links.opened`/`read`, so macros are
  never executed and the source is opened hidden/read-only (ADR 0020). The fetched grid is exactly
  what `core/links.fetched` already produces; the only difference is that the resulting state has
  `link = None`, so the chart owns the data afterwards.
- CSV options: the first line chooses the delimiter (as `core/links.csv_options` does today), and
  the import dialog offers the same. Encoding: UTF-8 with a BOM and the system default are tried;
  a wrong encoding produces replacement characters rather than an exception. Excel/ODS cells use
  LibreOffice's filters and need no options.
- The import replaces the whole data sheet. If the chart already has data, ask before replacing;
  one undo step restores the old state.
- A range with more than `links.MAX_CELLS` (10 000) is refused with the existing message.
- The imported grid must have at least two rows and two columns for a category/series chart; fixed
  column kinds (Gantt, scatter, bullet, box plot) validate their own shape and report the reason.
- *Import from file...* is not a link: the data does not update when the file changes. The dialog
  explains the difference and offers *Link instead*.

### Insert a chart from copied cells

- In Calc, copy a range; in Impress, *Insert chart from clipboard* creates a chart with that data.
  The clipboard is read as text/plain (TSV) and, where available, as HTML table; the TSV path is the
  reliable one on Windows and Linux.
- `core/table_import.py` parses TSV/CSV into a rectangular grid, detects a header row and a header
  column heuristically (first row text, first column text), and hands the grid to
  `core/datasheet.state_from_table`. The user can choose the chart kind; the default is a column
  chart.
- Clipboard access lives in `lo/clipboard.py`. Tests that need a visible document or the clipboard
  call `helpers.skip_on_headless_linux(...)` (see AGENTS.md); the parser is fully unit-tested.
- If the clipboard has only one column/row, insert a chart with one series/category rather than
  refusing.
- HTML tables are a stretch goal: `text/html` is available on most platforms, but parsing it without
  a dependency means a small, strict parser. Start with TSV and add HTML if the clipboard does not
  provide TSV on macOS.

### Update links when a deck opens

- A document setting `librecharts:auto-update-links` (stored like the scheme and the agenda). Default
  off, so existing decks keep the info-bar behaviour.
- When on, the document-open job updates every changed source after the view is complete (the info
  bar path already retries because `appendInfobar` fails for about a second, see AGENTS.md). If an
  update fails, the normal info bar appears with the reason; a successful update shows a short status
  message, not a modal dialog.
- The setting is a checkbox in the link dialog (*Update links when this presentation opens*) and in
  the sidebar's Document section. One document property, no per-chart setting.
- Security: the existing link rules apply (read-only, no macros, only file URLs or explicitly chosen
  sources). Auto-update never asks for a password; a protected source that needs one is reported and
  left unchanged.
- Undo: an automatic update on open adds one undo action per chart? That would flood the undo stack
  before the user does anything. The update uses `chart.redraw` without an undo action, like a deck
  build (ADR 0028): nobody undoes an update that happened on open. Manual *Update link* keeps its
  undo action.

### One source for several charts

- Today every chart stores its own `Link`. `lo/links.update` already opens each source once per
  update, so several charts with the same link are read efficiently.
- Add *Use this source for other charts...*: pick charts (or *all linked charts*) and copy the
  selected chart's `Link` to them, then update them in one step. This gives a deck one logical source
  without a new registry.
- A true source registry (one editable definition, charts reference it by id) is the next step: a
  document property with `id -> Link`, `ChartState.link` gains an optional `source_id`, and a chart
  without its own URL resolves through the registry. It removes duplication but makes a chart depend
  on a document property; a chart copied into another deck would lose its source unless the registry
  travels with it. The ADR must decide whether v1 stops at "same link copied" or implements the
  registry. The plan recommends the copy for M28 and a registry only if users ask for editing one
  definition.
- *Update all links* stays the single refresh command; with a shared source it reads the file once.

## Data model

- No `ChartState` change for file import and clipboard: they produce a normal state with `link=None`.
- Document property `librecharts:auto-update-links` (`"true"`/`"false"`), read/written by
  `lo/store.py`; no schema bump.
- If the shared-source registry is implemented: `Link.source_id: str = ""` and a document property
  `librecharts:sources` with JSON `{id: {url, sheet, range, relative}}`. Schema bump and migration;
  old links keep working without a source id.
- `core/table_import.py`: TSV/CSV parsing, delimiter detection, header heuristics, grid validation.
- `core/links.py`: a helper `imported(state, results, shown)` that is `fetched` without the link, and
  a `shared_with(state, link)` validation for copying a link.

## Approach

1. **File import first.** Extend the link dialog with an *Import* mode or add a sibling dialog that
   reuses its browser. Call `links.fetched` and then clear `link`; redraw and refresh the data sheet
   as one undo step. Test CSV, ODS and XLSX through `tests/lo`; the range rules are already tested.
2. **Clipboard.** Add `lo/clipboard.py` and `core/table_import.py`. Insert a chart with the parsed
   grid at the default position. Skip clipboard tests on headless Linux.
3. **Auto-update.** Add the setting to `store`, a checkbox to the link dialog/sidebar, and a branch in
   `lo/links.offer_update`: if enabled, update first, then show the info bar only for problems. Use
   the existing asynchronous retry so the document-open job does not touch an incomplete view.
4. **Shared source.** Start with *Use this source for other charts...* in the context menu and the
   sidebar. It copies `Link` values and calls the existing update path once. A registry is a
   follow-up ADR if needed.
5. **Docs.** README section on importing vs linking, the auto-update setting and the shared-source
   command. Update the extension description and the German/English messages, then `poe locales`.

## Affected modules

| Module | Change |
|---|---|
| `core/links.py` | `imported`, `shared_with`, size and shape helpers |
| `core/table_import.py` | New: TSV/CSV parsing and header heuristics |
| `core/datasheet.py` | `state_from_table` reuse; fixed-column validation hooks |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Import, clipboard, auto-update, share commands |
| `lo/linkdialog.py` | Import mode, auto-update checkbox, *Link instead* |
| `lo/importdialog.py` | Optional sibling dialog if the link dialog becomes too crowded |
| `lo/clipboard.py` | New: read text/plain, later text/html |
| `lo/links.py` | Auto-update branch, shared-source copy, no-undo redraw on open |
| `lo/store.py` | Auto-update document property; optional source registry |
| `lo/commands.py`, `lo/contextmenu.py`, `lo/sidebar.py` | Commands and UI |
| `lo/datasheet.py` | Refresh after import (existing path) |
| `tests/lo` | CSV/ODS/XLSX import, clipboard, auto-update, shared source |

## Tests

- `tests/core/test_table_import.py`: TSV/CSV with quotes, tabs, decimal commas, CRLF, empty cells,
  header detection, ragged rows, large grid rejection.
- `tests/core/test_links.py`: `imported` equals `fetched` minus the link; relative URL handling;
  shared-link validation; CSV delimiter options.
- `tests/core/test_datasheet.py`: `state_from_table` with imported grids; fixed-column kinds reject
  the wrong shape with a message.
- `tests/lo`: import a CSV, an ODS and an XLSX into a column chart (skip if filters are unavailable);
  undo restores the old data; clipboard insert with a visible document (skip headless Linux);
  auto-update on open with `hidden=False` (document-open jobs run for visible documents only);
  shared source updates every chart; a broken source leaves the charts unchanged and shows the info
  bar.
- Manual: encoding, delimiter and overwrite prompts; clipboard from Excel and Calc on Windows/macOS.

## Open questions

- Should *Import data...* replace the data sheet or append rows/columns? Replace is predictable;
  append needs a target cell and is a spreadsheet feature. Start with replace.
- Is `text/html` clipboard parsing needed on macOS where TSV may be missing? Check during
  implementation; a strict HTML-table parser is small.
- True shared source registry versus copied links: the registry is cleaner for editing, the copy is
  self-contained when a chart moves between decks. The ADR should weigh this before implementing.
- Auto-update on open can make opening a deck slow with many large sources. Add a progress/status
  message and a per-document "ask me" option? Start with off/on and the existing update all.
- Should an imported file be remembered as "last import folder"? LibreOffice's file dialog already
  remembers the last folder; no extra state.
- Auto-update and linked ODP/PPTX round-trips: the setting is a document property, which survives
  ODP; PPTX has no equivalent, so the setting resets to off after a PPTX save. Document this.

## Out of scope

- Live editing of an external file inside Impress (no embedded spreadsheet object).
- Database/ODBC sources, web URLs, Google Sheets.
- Automatically refreshing links while the deck is open (only on open and on demand).
- Importing think-cell data or chart definitions (non-goal).
