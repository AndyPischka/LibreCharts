# M33: Linked text fields (in-line data fields)

- Status: draft, to be agreed
- Milestone: M33
- Complexity: M (new link *target*, reuses the M11/M28 link machinery)
- Builds on: M11 (data links, ADR 0020), M28 (update on open, shared sources), M18 (update all links)

## Goal

think-cell can link any text field to a single spreadsheet cell, so a headline like
*"Revenue: €12.3m"* updates with the workbook. LibreCharts links only charts. This milestone links
**ordinary Impress text shapes** to a cell of an external Calc/Excel/CSV source: *Link text...* on
a selected text shape, *Update link(s)* refreshes it, and the deck's info bar / update-on-open
covers text links as well.

## Approach

### Model

- A text link is **not** a chart state. Store it on the shape itself: a small JSON blob in the
  shape's `Description` would clash with user text — instead use the shape's **Name** prefix
  (`librecharts-textlink:<id>`) plus a document-level registry, mirroring how charts are found.
  Decide in the plan review: per-shape user-defined attribute vs. registry keyed by shape name.
  Reuse `core/links.py`'s `Link` value object (source URL, relative URL, sheet, address) and its
  path/relative-URL helpers unchanged; the address is a **single cell** (`B2`, parsed as `B2:B2`).
- Registry lives in the document like the link bookkeeping of M11 (same store module charts use),
  so save/reload, copy and ODP/PPTX behave the same way. Copied shapes keep their own link.

### Reading and formatting

- `lo/links.py` already opens a source hidden/read-only and returns grids; add a single-cell read
  that returns the **formatted display string** of the cell (number format of the source cell, so
  "12,3 Mio. €" survives) with a raw-value fallback.
- The text shape's content is replaced by that string. The link only owns the shape's **whole
  text** in v1 — no in-line placeholders inside a longer paragraph (see open questions).
  Character/paragraph formatting of the shape is preserved (write via the text cursor, keep the
  first portion's attributes — see AGENTS.md pitfalls).

### UI and update flow

- New commands: *Link text...* (menu/context menu when a plain text shape is selected), *Update
  link*, *Remove link*, *Open source file* — the same entries charts have, sharing dialogs
  (`lo/linkdialog.py` if present, else the chart's link dialog) with a single-cell default.
- *Update all links*, update-on-open, the info bar and the deck audit (M29) treat text links like
  chart links: one file opened once per update, changed sources reported, nothing updated without
  asking. `poe deck update` refreshes them too.
- Number-format edits in the source are reflected on next update; manual text edits to a linked
  shape are overwritten on update (same contract as linked charts' read-only data sheets — show a
  hint in the link dialog).

## Affected modules

| Area | Modules |
|---|---|
| Link model, single-cell address, relative URLs | `core/links.py` (reuse), small additions for single-cell parse/format |
| Text-link registry | `core/model.py` or a new small `core/textlinks.py`; document store used by M11 |
| UNO: read cell display string, write shape text | `lo/links.py`, new `lo/textlinks.py` |
| Commands/dialogs/menu/sidebar | `lo/commands.py`, `core/menu.py`, `core/panel.py`, `core/messages.py`, `core/locales/*` |
| Update-all, info bar, audit, CLI | `lo/links.py` (update paths), `lo/audit.py`, `scripts/deck.py` |

ADR: yes — a short ADR for *links target non-chart objects* (extends ADR 0020).

## Test strategy

- `core/`: single-cell address parsing (`B2` ⇔ `B2:B2`), registry round-trip, relative-path
  handling, CSV vs spreadsheet sources.
- `tests/lo/`: link a text shape to a cell in a fixture ODS/XLSX/CSV; update changes the text and
  keeps formatting; *Update all links* covers charts and text in one pass; save/reload ODP and
  PPTX; copied shape has an independent link; remove link makes the text editable again.
- Info bar on changed source for a deck with only text links.
- `uv run poe check`, `uv run poe test-lo`; docs: README automation section, CHANGELOG, feature
  list, glossary term "text link".

## Open questions

- Whole-shape text only, or in-line placeholders (`{{B2}}`) inside a paragraph? Proposal:
  whole-shape in v1; in-line is a later milestone (needs run-level bookkeeping).
- Display string from the source's number format vs. LibreCharts number format dialog? Proposal:
  source's format first (least surprise), optional override later.
- Table cells as link targets? Out of scope for v1, but the registry design should not exclude it.

## Out of scope

- Linking images or other objects, Tableau links, bidirectional editing.
- Linking to cells inside the same document's chart data sheets (external files only, as M11).
