# M29: Automation round-trip, deck audit and batch operations

- Status: proposed
- Milestone: M29 (7.0)
- Builds on: M18 automation (ADR 0028), M19 design check (ADR 0029), M20 CSV export, M11 links
- Decision: ADR for deck specification version 2 (slide + box) and the audit report format

## Goal

M18 can build a deck from a template and a JSON specification, and M19 can check a finished deck
against a corporate design. The workflow still stops at the last step: an existing deck cannot be
exported back into a specification, nobody can see what is wrong with a deck in one place, and a
format change has to be applied chart by chart. M29 closes the loop for build pipelines and for
authors who maintain a deck by hand.

## Scope

### Export an existing deck as a specification

- New command *Export deck specification...* (menu, sidebar, Python API, CLI). It walks the slides
  and writes one chart entry per LibreCharts chart: its `ChartState` (kind, data, options, format,
  annotations, labels), the slide it sits on and its frame `box` (1/100 mm).
- The current specification only knows placeholders. Version 2 adds an alternative:
  ```json
  {
    "version": 2,
    "charts": [
      {"slide": 3, "box": [1200, 2000, 12000, 7000], "kind": "column", "data": [[...]]}
    ]
  }
  ```
  A chart entry needs exactly one of `placeholder` or `slide` + `box`. `slide` is 1-based in the
  file (users count slides from 1), converted to 0-based in `lo/`; `box` is `[x, y, width, height]`
  in 1/100 mm.
- The exported specification rebuilds the charts, not the text, pictures or master slides. The user
  supplies the same template (or a cleaned copy of the deck) to `poe deck build`; that limitation is
  documented and is the reason this is called a "chart specification", not a deck clone.
- Version 1 specifications keep working unchanged. Version 2 is written by the exporter; the parser
  accepts both.
- A chart whose state cannot be read is exported as a placeholder-less entry? No: the export fails
  with the list of broken chart ids, so the pipeline never writes a half specification. Add
  `--skip-broken` later if needed.
- Chart order: slide order, then shape order. Stable output helps diffing two exports in version
  control.

### Deck audit

- New `poe deck audit deck.odp [--json] [--fix]` and *Audit presentation...* in the UI.
- Findings, each with slide, shape/chart id, a message key and a detail:
  - unreadable or older-schema chart state;
  - a group named `librecharts:<id>` without a state, or a state without a group (orphans);
  - dangling annotation/label/focus indices after a data edit;
  - missing alternative text on charts, elements and tables;
  - broken, stale or never-updated data links;
  - charts outside the slide or outside the design margins;
  - corporate design deviations (reuse `core/designcheck.py`; pass the design file if given);
  - charts whose data sheet is empty or smaller than the layout needs;
  - support data: LibreOffice version, extension version, chart count, schema versions, source
    paths (not their contents).
- The text report groups findings by slide and prints a summary. `--json` writes the same findings as
  machine-readable JSON for a pipeline.
- Exit code 3 when there are findings that `--fix` would not or could not fix, like `check`. Exit 0
  when clean or everything was fixed, 1 for an unreadable deck.
- `--fix` is deliberately narrow in v1: regenerate alternative text, update stale links, and apply
  the corporate design fixes when `--design` is given. It never deletes charts, clears annotations
  or changes data. Each category is one undo action in the UI; a CLI run saves the result.
- GUI: a list dialog (`lo/auditdialog.py`) with one row per finding; selecting a row jumps to the
  slide and selects the chart or shape. Buttons *Fix selected* and *Fix all fixable*. Modal dialogs
  cannot be driven headlessly, so the finding logic lives in `core/audit.py` and is tested there.

### Batch operations

- *Apply format to all charts of this kind*: copies the format and series colours of the selected
  chart to every LibreCharts chart of the same kind in the deck, in one undo action. This is
  `core/format.apply` plus a document-wide loop; it uses the existing `lo/samescale.py` style of
  collecting charts and redrawing.
- *Apply format to all charts*: the same across kinds where the format supports it (a pie has no
  axis; the function skips unsupported fields and reports how many charts changed).
- *Set alternative text for all elements* (part of audit fix) and *Update all links* (exists).
- A batch data replacement is already covered by `build` with a new specification; do not add a
  second path.

## Data model

- `core/deck.py`:
  - `ChartSpec` gains `slide: int | None`, `box: tuple[int, int, int, int] | None`; validation
    requires exactly one of `placeholder` and (`slide` and `box`).
  - `VERSION = 2`; the parser accepts 1 and 2. A version 1 entry with `slide`/`box` is rejected.
  - `to_spec(charts: Sequence[ChartSpec]) -> str` writes a deterministic JSON (sorted keys? preserve
    chart order, `json.dumps(..., ensure_ascii=False, indent=2)`).
- New `core/audit.py`: `Finding` dataclass (`kind`, `slide`, `shape`, `detail`, `fixable`),
  `audit(...)` collecting the pure checks, `report(findings, locale, json=False)`.
- No `ChartState` change. The audit reads existing states; it does not store its own data.
- `core/messages.py` gets the finding titles and fix messages in English and German.

## Approach

1. **Spec v2 in core.** Extend parsing/validation and add `to_spec`. Test both versions, a mixed
   spec, a missing box, a zero-sized box, and slide 0/negative. The exporter builds `ChartSpec`
   objects from states and frames.
2. **Exporter in `lo/`.** Walk slides and `store.all_charts`, read state and `render.layout_box`,
   write the JSON. Add a CLI command and an API function. Save via the file dialog or `--out`.
3. **Build path for boxes.** `lo/deck.py` needs to insert at a box when there is no placeholder. It
   must not remove a placeholder; it inserts on the given slide at the given box. Validate that the
   slide exists before drawing anything.
4. **Audit collection.** Write `core/audit.py` first with synthetic findings; then `lo/audit.py`
   collects real shapes. Reuse `core/designcheck.py` and `core/links.py` rather than re-implementing
   checks. Add the CLI command and exit codes.
5. **Audit dialog.** A list control with slide numbers and messages; selection jumps with
   `controller.setCurrentPage` and `controller.select`. Fix buttons call the same functions as the
   CLI. Test the dialog by hand (headless limitation).
6. **Batch format.** Add the command and a menu entry; one undo action across all redrawn charts.
   Reuse the "collect, lock undo, apply, one action" pattern of `lo/samescale.py`.
7. **Docs.** README section for `poe deck audit` and spec v2; update ADR 0028 or write a new ADR.
   Add the finding keys to `messages.py`, then `poe locales`.

## Affected modules

| Module | Change |
|---|---|
| `core/deck.py` | Spec v2, `slide`/`box`, `to_spec`, validation |
| `core/audit.py` | New: findings and report |
| `core/designcheck.py`, `core/links.py` | Reused checks; small helpers if needed |
| `core/format.py` | Batch apply helper (supports per kind) |
| `core/cli.py` | `audit`, `export` subcommands and arguments |
| `core/messages.py`, `core/locales/*.json` | Finding and CLI texts |
| `lo/deck.py` | Export, box insertion, deterministic output |
| `lo/audit.py` | New: collect findings from a document |
| `lo/auditdialog.py` | New: report list and jump-to-slide |
| `lo/commands.py`, `lo/sidebar.py`, `lo/contextmenu.py` | Commands and entries |
| `lo/worker.py` | `audit` and `export` commands, exit codes |
| `api.py`, `scripts/deck.py` | Public functions and CLI help |
| `extension/Addons.xcu`, `extension/images/` | Audit/export entries |

## Tests

- `tests/core/test_deck.py`: v1 and v2 parse, exactly-one-of validation, slide/box bounds, `to_spec`
  round-trip, deterministic output, export -> parse -> build spec equality.
- `tests/core/test_audit.py`: each finding kind with synthetic inputs; clean deck has none; report
  text and JSON; fixable flags.
- `tests/core/test_format.py`: batch apply skips unsupported options and reports changed charts.
- `tests/lo`: build from a v2 spec with slide+box; export a deck and rebuild its charts; audit a deck
  with a broken link/orphan/old schema; `--fix` updates alt text and links; exit code 3; audit dialog
  manual.
- `tests/lo`: batch format on a deck with several kinds; one undo step; resize and reload.
- CLI: `--json` output is valid JSON; `audit` on a missing file returns 1; `check` behaviour
  unchanged.

## Open questions

- Is slide+box the right export model, or should the exporter create placeholders in a copy of the
  deck? Slide+box is simpler and does not modify the deck; the template still owns the text and
  layout.
- Should an exported spec include the template path and the design file? A `"template"` field would
  make a build one command. It also bakes a local path into the file. Add an optional `"template"`
  only if the pipeline needs it.
- Audit `--fix` scope: alt text and links are safe; design fixes need a design file. Data repairs
  (clamping dangling indices) are not safe and stay report-only.
- Orphan detection: a group with the prefix but no property may be a user shape that happens to be
  named that way. Report, never delete.
- Finding IDs for pipelines: a stable `code` (`ORPHAN_CHART`, `STALE_LINK`, ...) in the JSON is
  better than localized text. Add codes in the ADR.
- Large decks: collecting all shapes and links can take seconds; the audit is on demand, not on
  every modify event. Reuse the lesson from `lo/resize.py`.
- PPTX: document properties survive, but alternative text of groups is dropped by the filter
  (known limit). The audit will report it as missing after a PPTX round-trip; that is correct but
  may annoy. Document it.

## Out of scope

- Exporting slide text, pictures, master slides or animations (the template owns those).
- A web service or CI action; the CLI is enough.
- Automatic data repair or schema upgrade of old charts (the state loader migrates on read; the
  audit only reports).
- A general plugin API beyond `librecharts.api`.
