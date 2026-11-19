# M30: Design check, theme and accessibility

- Status: proposed
- Milestone: M30 (7.0)
- Builds on: M8 colour schemes (ADR 0016), M19 design check (ADR 0029), M20 accessibility (ADR 0030),
  M21 languages (ADR 0031)
- Decision: ADR for master/layout/picture checks, the design report and theme integration

## Goal

The corporate design check covers shapes on slides, but not the master slides, layouts or pictures,
and its result is a message rather than a navigable report. The colour scheme is edited as JSON, a
colour-blind reader has only the pattern switch, and alternative text exists for charts only. M30
turns the design check into a review tool and makes the deck's look and accessibility manageable
from the UI.

## Scope

### Design check for masters, layouts and pictures

- `lo/designcheck.collect` also reads `doc.getMasterPages()` and the layout shapes on them. A
  `ShapeInfo` gains a container/source:
  - `source: Literal["slide", "master"]`, `slide` for slides (0-based) and `master` for master
    pages (0-based).
  - `path` stays the index path inside the page; the handles map is keyed by `(source, index, path)`.
- Master shapes are checked for colours and fonts. Position/margin checks on masters are **opt-in**
  (`check_masters: bool` in the design file, default off): backgrounds, bands and logos often bleed
  to the edge on purpose, and flagging every master would make the check noisy.
- Pictures (`GraphicObjectShape`) become `kind="picture"`: no fill, line or font checks; position and
  margin checks apply. Optionally the design file lists allowed image hashes (SHA-256) under
  `"images"`; an unknown picture is reported with its name and slide. Hashing is `hashlib` from the
  standard library, no dependency. A picture can be large; hash the graphic's byte stream, not its
  rendered pixels.
- Layout placeholders are part of the master page and are covered by the same pass. Empty
  presentation placeholders are skipped, as `_portions` already does.
- The document scheme check stays as is. A deck without charts is not forced onto the corporate
  palette, but master/slide shapes still are.

### Report dialog

- `core/designcheck.Result` gains enough location data for a list: source, slide/master index, path,
  label, issue, actual and expected. `Finding` already has slide/path/label; extend it with `source`
  and `master`.
- *Check corporate design...* opens a report dialog before fixing:
  - a list grouped by slide, with a count summary;
  - selecting an entry jumps to the slide and selects the shape (or enters the group);
  - buttons *Fix all*, *Fix selected* and *Close*.
- The CLI keeps the existing report text and exit code 3. `--fix` still fixes everything.
- If the check is clean, a short message is enough; the dialog only opens with findings.
- The dialog is modal and built in code (`lo/designreport.py`), like the other dialogs. Headless
  tests cannot drive it; the list model and fix selection are `core/` functions.

### Theme colours and fonts

- A new scheme source *From the master*: read the master page's background, title and body text
  styles and derive a `Scheme`:
  - palette: the document's theme colours if LibreOffice exposes them; otherwise the colours used by
    the master's title/body/accent shapes, filled up from the current scheme;
  - text and background from the master;
  - font name and size from the master's title/body.
- This is a feasibility item: the UNO theme API differs between LibreOffice versions and some
  master pages have no explicit colours. If the derivation is unreliable, the fallback is "use the
  master's font and background, keep the current palette" and the ADR records the limit.
- The scheme remains the single source for chart colours; *From the master* only creates a scheme,
  it does not make charts live-follow the master. A live link to the master would redraw every chart
  on a master change and is out of scope.

### Colour-blindness simulation

- `core/style.py` gets colour-vision simulation for deuteranopia, protanopia and tritanopia (the
  standard LMS matrices), plus `contrast_ratio` and a check that neighbouring palette entries stay
  distinguishable under each simulation.
- Two user-facing pieces:
  1. **Built-in safe schemes**: three palettes derived from the default palette and checked under the
     corresponding simulation. They appear beside Default/Grey/High contrast.
  2. **Preview**: *Preview colour-blindness* in the Document section renders the selected chart (or
     all charts) with a simulated scheme, then restores the real one. This is a temporary redraw,
     not a document change; it is one undo-neutral operation and must not fire modify events in a
     loop. If a full preview is too expensive, start with the safe schemes and a palette report.
- Patterns (M20) remain the primary accessibility feature; simulation helps choose colours, not
  replace patterns.

### Alternative text for every element

- `core/alttext.py` gains descriptions for:
  - Harvey balls and check marks (`"Harvey ball, 75 %"`, `"Check mark: yes"`),
  - the agenda (`"Agenda with 4 chapters: ..."`),
  - tables (headers and a compact row summary, M25),
  - process/pyramid/chevron graphics and icons (M26; an icon gets a short name, a decorative icon
    can be marked as such),
  - pictures (the user's existing description is kept; the check reports a missing one).
- `lo/elements.py`, `lo/agenda.py`, `lo/graphics.py` call `render.describe` with the generated text,
  like charts do. The descriptions follow text edits and element state changes.
- The audit (M29) reports missing alternative text; M30 generates it. A user-typed description always
  wins: before a redraw, compare the shape's current description with the description generated from
  the previous state; overwrite only when it is empty or still equals the generated text. A *Restore
  automatic text* command clears a manual description. This also fixes the current chart behaviour
  instead of extending it.
- Decorative shapes: a *Mark as decorative* command sets an empty title and a marker in the shape
  name, so the audit does not report them.

### Palette editor

- *Edit colour scheme...* opens a dialog with:
  - a grid of palette entries (up to 32) with a colour swatch and a hex field;
  - text, line and background colours;
  - font name and size;
  - name of the scheme;
  - *Load...*, *Save as...*, *Apply*, *Cancel*.
- Colour entry is a hex field plus a preview; if the toolkit offers a colour picker control, use it,
  otherwise the hex field is the fallback (no custom control drawing).
- The dialog edits a `Scheme` value; validation and JSON stay in `core/style.py`. Applying is one
  undo step and redraws all charts via `chart.apply_scheme`.
- The sidebar keeps the quick scheme switch and file load/save; the editor is for creating a
  corporate palette without hand-editing JSON.

## Data model

- `core/designcheck.py`:
  - `ShapeKind` gains `"picture"`.
  - `ShapeInfo` gains `source: Literal["slide", "master"] = "slide"` and `master: int | None = None`;
    `Finding` and `Fix` carry the same location.
  - `Rules` gains `check_masters: bool = False` and `images: tuple[str, ...] = ()` (SHA-256 hex).
  - `rules_from_json` reads `check.check_masters` and `check.images`.
- `core/alttext.py`: new functions, no state change; decorative markers live in the shape name.
- `core/style.py`: simulation functions and safe schemes; `Scheme` unchanged.
- No `ChartState` change and no schema bump. Document properties are unchanged.

## Approach

1. **Location model first.** Extend `ShapeInfo`/`Finding`/`Fix` and the handles map, then collect
   master pages. Existing slides must produce identical findings; add regression tests before
   adding masters.
2. **Pictures.** Add `kind="picture"` with box-only checks and optional hashes. Test with a fake
   graphic shape in `tests/lo` (or a real PNG inserted into a test deck).
3. **Report.** Build the list model in `core/designcheck.py` (`report_rows(result, locale)`), then the
   dialog in `lo/designreport.py`. Reuse the jump-to-slide pattern from the audit dialog (M29).
4. **Theme.** Spike the UNO theme API on 25.8 and 26.8; if unstable, derive from master text styles
   and document the fallback in the ADR.
5. **Simulation and safe schemes.** Add the math and tests first; generate the three palettes and
   check them under simulation; only then add the preview command.
6. **Alt text.** Add one kind at a time (elements, agenda, table, graphics, pictures), with tests for
   the sentence and the language/number format. The audit from M29 reports what is missing.
7. **Palette editor.** `core/style.py` already validates `Scheme`; the dialog only moves values. Test
   the form model (hex parsing, add/remove palette entry, max 32) in `core/`, the dialog by hand.
8. **Docs.** README section on the report, master checks, safe schemes and alt text. Update the
   corporate design file example with `check_masters` and `images`.

## Affected modules

| Module | Change |
|---|---|
| `core/designcheck.py` | Source/master/picture, rules, report rows |
| `core/alttext.py` | Element, agenda, table, graphic and picture descriptions |
| `core/style.py` | Simulation, contrast, safe schemes |
| `core/messages.py`, `core/locales/*.json` | New UI strings |
| `lo/designcheck.py` | Collect masters/pictures, handles by source, fixes |
| `lo/designreport.py` | New: report dialog and jump-to-slide |
| `lo/elements.py`, `lo/agenda.py`, `lo/graphics.py` | Describe alternative text |
| `lo/render.py` | Generic `describe` for elements (already exists for charts) |
| `lo/schemedialog.py` | New: palette editor |
| `lo/commands.py` | Report, editor, preview commands |
| `lo/sidebar.py` | Document section entries |
| `lo/chart.py` | `apply_scheme` for preview and editor |
| `extension/Addons.xcu`, `extension/images/` | Entries and icons |
| `tests/lo` | Master/picture check, alt text, report dialog manual |

## Tests

- `tests/core/test_designcheck.py`: existing slide findings unchanged; master findings gated by
  `check_masters`; picture position; image hash allowlist; report rows with source/slide labels;
  fixes for master shapes addressed correctly.
- `tests/core/test_alttext.py`: every element kind, agenda count, table summary, graphic labels,
  decorative marker, language and number format.
- `tests/core/test_style.py`: simulation matrices map primaries to expected hues, contrast ratio,
  safe palettes pass their own simulation, scheme JSON with new fields (if any).
- `tests/lo`: a deck with a master colour deviation, a picture outside the margins and an unknown
  image; check/fix; undo; reload; alt text on Harvey balls and agenda after an edit; a typed
  description survives a data edit and *Restore automatic text* regenerates it; palette editor by
  hand.
- Manual: report dialog navigation, colour picker/hex entry, preview restoration.

## Open questions

- Master position checks: default off is safe, but then "check master slides" means colours/fonts
  only unless the design file opts in. Is that clear enough in the report?
- Theme API: if LibreOffice exposes no stable theme colours, *From the master* may be a font and
  background import only. The ADR should state the limit rather than promise a live theme.
- Image allowlist: hashes break when a logo is re-exported with different metadata. Offer a name
  allowlist as well, or only report unknown pictures without failing the check.
- Detecting manual text: comparing the current description with the previous generated text works for
  charts and elements that have stored state. A PPTX round-trip drops group descriptions (known
  limit), so a manual text can be lost by the filter; document that and report it in the audit.
- Should *Restore automatic text* be per element or for all elements on a slide? Start per element; a
  slide-wide command can be added if it is needed.
- Preview mode: restoring the scheme must not add an undo action or modify the document; if a
  redraw is too slow for a whole deck, preview the selected chart only.
- Palette editor: a colour picker control is toolkit-dependent; the hex field is the guaranteed
  path. Adding/removing palette entries needs a sensible maximum (32) and a reset to the built-in.

## Out of scope

- Live theming where charts follow master edits automatically.
- Pixel-level accessibility simulation of pictures or the whole slide.
- Automatic colour choice for arbitrary user palettes; the safe schemes are fixed.
- A full corporate identity editor (logos, slide layouts, master design).
