# M27: Chart templates and favourites

- Status: proposed
- Milestone: M27 (6.0)
- Builds on: M1-M20 (chart state, format, annotations, colours), M18 (deck specification, ADR 0028)
- Decision: new ADR for the template file format, the template folder and the CLI/API surface

## Goal

A well-formatted chart is hard to reproduce. *Copy chart format* transfers the look between two
charts on one slide, but there is no way to keep a chart as a reusable starting point for the next
deck. M27 turns a chart's complete state (kind, options, format, colours, annotations, moved labels
and sample data) into a named template that can be inserted from the sidebar, the menu or a deck
specification.

This is the "chart templates or favourites" candidate already named in the roadmap. It multiplies
the value of every format feature of M6-M20 without adding new drawing code.

## Scope

### What a template contains

- The chart kind and its options (`grouping`, `percent`, `sort`, `doughnut`, `horizontal`, `stacked`,
  `range`, `errors`, `lines`, `secondary`, `pareto`, ...).
- The format (`axis`, gridlines, number format, language, markers, patterns, legend, font size).
- Series colours (`colors`), annotations and moved-label offsets.
- Sample data (`cells` and `values`), so the template opens as a visible chart rather than an empty
  frame.
- A name and an optional description for the gallery.
- **Not** the data link (`link`) and **not** the same-scale group (`scale_group`): both belong to the
  document or the source file, not to the look. Saving strips them; a template can still be a
  starting point for a linked chart, the user links it after insertion.
- Annotations and label offsets refer to data sheet indices. When the template's data is replaced by
  the deck specification, dangling indices are ignored exactly like after a data edit (ADRs 0010,
  0023). The template author should keep the sample data shape meaningful.

### File format

A template is a small JSON object around the existing chart state:

```json
{
  "version": 1,
  "name": "Stacked revenue",
  "description": "Three years, axis and value labels",
  "state": { "kind": "column", "grouping": "stacked", ... }
}
```

- `state` is exactly what `core/state_io.to_json` writes, so the template inherits schema migrations
  and validation. `core/templates.py` wraps and unwraps it.
- Unknown top-level fields are rejected; unknown `state` fields are handled by `state_io` as today.
- A template saved by a newer LibreCharts is refused with a clear message, like a chart state.
- The file extension is `.json` (a custom extension would make email/web sharing harder).

### Template folder and gallery

- Default folder: `<LibreOffice UserConfig>/librecharts/templates`, found through the
  `com.sun.star.util.PathSettings` service (`UserConfig`), with `Path.home()` as a fallback. The
  folder is created on first save; a missing folder is not an error.
- *Save chart as template...* writes the selected chart to the folder after asking for a name (the
  file name is derived from it, sanitised). If a file exists, ask before overwriting.
- *Insert from template* lists the files in the folder. The menu shows a submenu, the sidebar lists
  buttons like the colour schemes do. No thumbnails in v1: rendering a preview for every template
  would cost a LibreOffice round trip and is not needed for a short list.
- A second command *Save template as file...* / *Open template file...* allows sharing a template
  outside the folder. The file dialog lives in `lo/`; the JSON handling in `core/`.
- Deleting/renaming templates is done in the file manager in v1. A gallery manager is a later item.

### Insertion and the deck specification

- Insert at the current selection if it is a chart? No: insert at the slide centre with the standard
  chart size, selected, so the user can move it. If the template has a saved size? Size is not part
  of `ChartState` (the frame is document geometry), so the default size applies.
- The new chart gets a fresh id and its own state; editing it never touches the template.
- Deck specification: a chart entry may use `"template": "stacked-revenue"` instead of spelling out
  `kind`, `format`, options and sample data:
  ```json
  {"placeholder": "revenue", "template": "stacked-revenue", "data": [[...]]}
  ```
  `data` overrides the template's sample data; every other field still wins over the template when
  present. Resolution order for the name: a path relative to the specification file, then the
  template folder, then an absolute path. `core/deck.py` gets the template state through a loader
  callback so it stays pure and testable without the user's folder.
- Python API: `librecharts.api.insert_chart(..., template=...)`; no new module-level dependency.

## Data model

- New `core/templates.py`:
  - `Template` dataclass: `name`, `description`, `state: ChartState`.
  - `to_json(template)` / `from_json(text)`; validate name (1..80 chars), description (0..200),
    file name safety.
  - `stripped(state)` removes `link` and `scale_group` and resets the id? `ChartState` has no id;
    the id is the group name/store anchor.
  - `file_name(name)` sanitises a name for the file system (no `<>:"/\|?*`, no leading dot).
- No change to `ChartState`; no schema bump for templates themselves. The nested state keeps its own
  schema version.
- `core/deck.py`: `ChartSpec` gains an optional template state; parsing applies the template first
  and the entry fields afterwards. Template loading is injected, so tests use a dict of states.
- New `core/messages.py` keys for save/insert/overwrite/errors.

## Approach

1. **Core format and tests.** Implement `core/templates.py` over `state_io`, including stripping and
   validation. Test round-trip, a template saved by a newer schema, and a malformed state.
2. **Folder access in `lo/`.** `lo/templates.py` resolves the folder via `PathSettings`, lists
   `*.json`, creates the folder, reads/writes files. Keep all UNO in `lo/`; `core/` receives text.
3. **Commands.** `SaveTemplate` (selected chart -> dialog -> file), `InsertTemplate?name=...`,
   `SaveTemplateFile`, `OpenTemplateFile`. Each insert is one undo action; saving a file is not a
   document change and needs no undo.
4. **Sidebar and menu.** Add a *Templates* section to `core/panel.py` with one button per template
   (like `schemes`), plus *Save chart as template...*. The menu has the same commands. Texts in
   English and German, then `uv run poe locales`.
5. **Deck specification.** Extend `core/deck.py` with the optional template, and `lo/deck.py` with a
   loader that resolves the name relative to the spec file and the template folder. Document one
   example in the README.
6. **Docs.** A short section in the README; mention the folder location and the "sample data is
   replaced" rule. No new ADR? The file format and resolution order are lasting decisions, so an ADR
   is required by AGENTS.md.

## Affected modules

| Module | Change |
|---|---|
| `core/templates.py` | New: template wrapper, validation, file name |
| `core/deck.py` | Optional template state, precedence rules |
| `core/state_io.py` | No change; reuse `to_json`/`from_json` |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Template entries and texts |
| `lo/templates.py` | New: folder resolution, list, read, write |
| `lo/commands.py` | Save/insert/open commands and dialogs |
| `lo/deck.py` | Resolve and load templates for a build |
| `lo/sidebar.py` | Render the template buttons |
| `extension/Addons.xcu`, `extension/images/` | Menu/toolbar entries, icons |
| `README.md`, `ARCHITECTURE.md`, `docs/glossary.md` | Template term, folder, CLI example |

## Tests

- `tests/core/test_templates.py`: round-trip, strip link/scale, name validation, file-name
  sanitising, newer schema refused, malformed JSON, empty state data.
- `tests/core/test_deck.py`: template + overrides, data override, unknown template name, precedence,
  malformed template, placeholder still required.
- `tests/lo`: save a chart as a template, list it, insert it, undo, edit the copy without changing
  the file; insert from a shared file; build a deck with a template via `poe deck`; missing folder
  is created.
- Manual: sidebar list after adding a file in the folder; overwrite prompt.

## Open questions

- Should templates be per-document as well as per-user? A document could carry its own templates in a
  custom property. It makes decks self-contained but duplicates state and complicates "save".
  Start with the user folder and a file-based sharing path.
- Thumbnails in the gallery: render on demand to a PNG and cache? Nice, but not v1.
- Does a template keep moved-label offsets? They may point at labels that the template's sample data
  still has. Yes, keep them; if data is replaced, dangling offsets are ignored.
- Should the template store the chart's size and position? `ChartState` does not; insertion uses the
  default size. A "layout template" is a different feature (deck template, M18).
- Template name vs file name: allow renaming in the gallery, or treat the file name as the name?
  Start with the file name as the identity and a `name` field for display.
- How are template versions upgraded? Through `state_io` migrations when read; saving again writes
  the current schema. A template folder shared between 5.0 and 6.0 users will produce newer files
  that 5.0 cannot read; the error message must say so.

## Out of scope

- A template marketplace, cloud sync or a thumbnail gallery.
- Templates for slide elements, agendas or tables (a chart template is a chart).
- Live-linked "master charts" that update all copies when the template changes.
- Import of think-cell or PowerPoint chart templates (non-goal).
