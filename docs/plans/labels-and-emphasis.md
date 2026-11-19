# M22: Labels, emphasis and callouts

- Status: proposed
- Milestone: M22 (6.0)
- Builds on: M13 (moved labels, ADR 0023), M14 (annotations), M6/M20 (format, patterns)
- Decision: new ADR before implementation (label overrides, focus and chart notes in `ChartState`)

## Goal

A chart should be able to carry one message. Today every value label is produced by the layout, all
series have the same visual weight, and a source or a short comment has to be a separate text box
that does not follow the chart. M22 gives the user control over individual labels, a way to mute
everything that is not the point, and text that belongs to the chart.

## Scope

### Per-label control

- Hide one value or total label.
- Replace its text with a short custom string (at most 80 characters, like a group bracket).
- Reset a moved label to its layout position.
- Keep the existing drag-to-move behaviour of M13; hiding and custom text are additional properties
  of the same label identity (`LabelKey`).

The label picker must work on every chart kind that emits movable labels: column, bar, waterfall,
Mekko, line, area, pie, scatter, butterfly, Gantt (bar labels), Pareto (M24) and the new kinds.
Labels that the layout already marks `hidden` because they do not fit stay hidden until moved, as
before.

### Focus mode

- Highlight any number of series and/or categories; every other series or category is drawn in a
  muted colour. A data point is focused when its series is selected **or** its category is selected
  (union), so a chart can emphasise two series and one category at the same time.
- Muting must keep text readable: a muted fill still picks black or white text by contrast.
- The mode is a chart option (`ChangeChart?focus=...`), one undo step, and survives data edits and
  sorting. An index that no longer exists is ignored like a dangling annotation index.
- Series focus is offered by name with a checkbox. Category focus is offered after a pick, or by
  category name when the list is short; the sidebar lists both sets and clears them together.
- Annotations stay visible. An arrow that belongs to a muted series or category uses the muted line
  colour, so the annotation does not become the loudest element.

### Callouts and source line

- A chart-level source string, drawn at the bottom-left in the axis font size and included in the
  alternative text. When it is set, the layout reserves a footer band so value labels do not collide.
- A small number of free callout texts per chart, each anchored at a relative position (fractions of
  the layout box, like label offsets are absolute). A callout may be empty of a leader line in v1;
  leader lines to a label or segment are a later extension.
- Both are edited in a dialog; a callout can be moved with the existing *Move labels* session once
  the session can also see note shapes.

### Typography

- `Format.font_size`: an optional per-chart override of the scheme font size (`None` keeps the
  scheme value). It is a format field, so *Copy chart format* copies it; source and notes are chart
  content and are not copied.
- `Format.legend`: top, right, bottom or left. The current horizontal band above the plot is
  `top` and stays the default, so existing charts do not change.
- Automatic shrinking of labels when a chart becomes small is **not** part of M22: `core/` has no
  font metrics. It needs a separate measurement/estimate design.

## Data model

- Extend the label record (`LabelOffset` today, possibly renamed `LabelOverride`):
  `key: LabelKey`, `dx`, `dy`, `hidden: bool = False`, `text: str = ""`.
- New `Focus` dataclass: `series: tuple[int, ...] = ()`, `categories: tuple[int, ...] = ()`, at
  least one of them non-empty, unique and non-negative indices. `ChartState.focus: Focus | None`.
  The two sets are independent, so both can be filled; a primitive is muted only when its series and
  its category are both outside the focus.
- New `Note` dataclass: `text: str`, `x: float`, `y: float` in 0..1 of the layout box. `ChartState.notes:
  tuple[Note, ...]`.
- `ChartState.source: str = ""`, at most 200 characters.
- `Format.font_size: float | None` (4..72) and `Format.legend: Literal["top", "right", "bottom",
  "left"] = "top"`.
- Schema version bump and a migration in `core/state_io.py`: old label offsets load with
  `hidden=False`, `text=""`; no focus, notes or source; font size `None`; legend `top`.
- Validation: at least one focus index; every focus index non-negative and unique within its set;
  note coordinates finite and in 0..1; label text at most 80 characters.

## Approach

1. **Core model and migration.** Add the fields and tests before touching a layout. Keep old JSON
   readable in both directions? State is forward-only: a 5.0 LibreOffice cannot read a 6.0 chart, so
   the release notes must say so (as with every schema bump).
2. **Primitive support for muting.** Add `muted: bool = False` to `Rect`, `Polygon`, `Polyline`,
   `Marker`, `Bubble` and `Text`. Layouts set it from `state.focus`; the renderer mixes the series
   colour towards the background (about 75 %) and keeps `text_on` contrast. This puts the decision in
   `core/` where it is testable, not in the UNO renderer.
3. **Label overrides.** `core/labels.py` already knows how to find a `LabelKey` after layout. Apply
   hidden/custom text there: replace the `Text` primitive's `text`/`hidden` before offsets are
   applied. The layout remains a pure function.
4. **Label identity in shapes.** When the renderer creates a label shape, put the `LabelKey` into the
   shape name (`librecharts-label:<role>:<category>:<series>`). `lo/labels.py` can then map a selected
   child to its key instead of guessing from boxes. Names inside the group are not visible to the user.
5. **Commands and UI.** `ChangeChart?focus=series&index=2&on=true` (and `...&on=false`),
   `ChangeChart?focus=category&index=1&on=true`, `ChangeChart?focus=none`,
   `ChangeChart?label=value&category=1&series=0&hidden=true`, `SetLabelText?...`,
   `SetSource?text=...`, `AddNote?text=...`, `ClearFocus`. Text goes through dialogs
   (`lo/textdialog.py` or a new `lo/labeldialog.py`), because a query string is not a text editor.
   Every command is one undo step via `lo/undo.py`.
6. **Typography plumbing.** `lo/chart.py` builds the `Look` from the scheme and `state.format`; add
   the optional font size there. `core/layout/common.py` gets `legend()` with a position and a helper
   for the band each layout reserves.
7. **Alt text.** The source line is appended to the description; custom label text is not used for
   the data description (it may be marketing text), but a note can be appended in a separate
   sentence. Decide in the ADR.

## Affected modules

| Module | Change |
|---|---|
| `core/model.py` | `LabelOverride`, `Focus`, `Note`, `source`, format fields, validation |
| `core/state_io.py` | Schema bump and migration |
| `core/labels.py` | Apply hidden/custom text; keep offsets |
| `core/primitives.py` | `muted` flags |
| `core/layout/*.py` | Focus muting, source/note primitives, legend positions, font size is renderer-only |
| `core/layout/common.py` | `legend(position)`, band helper, muted helpers |
| `core/format.py`, `core/options.py` | Parse `font_size`, `legend`, `focus` |
| `core/alttext.py` | Source and notes |
| `core/menu.py`, `core/panel.py`, `core/messages.py` | Entries, status, both languages |
| `core/picking.py` | Category focus pick if offered; label picking lives in `lo/labels.py` |
| `lo/render.py` | Muted colours, label shape names, per-chart font size |
| `lo/labels.py` | Label key from shape name, note shapes, edit/hide/reset |
| `lo/commands.py`, `lo/contextmenu.py`, `lo/sidebar.py` | Commands and UI |
| `lo/textdialog.py` / new `lo/labeldialog.py` | Label, source and note dialogs |
| `lo/chart.py` | Build `Look` with format overrides |
| `extension/Addons.xcu`, `extension/images/` | Menu/toolbar entries and icons |

## Tests

- `tests/core/test_model.py`: validation and default compatibility of every new field.
- `tests/core/test_state_io.py`: 5.0 JSON loads with old defaults; new JSON round-trips; malformed
  overrides raise `StateError`.
- `tests/core/test_labels.py`: hidden, custom text, reset, duplicate keys rejected.
- Layout tests for every kind: muted primitives for single and mixed focus sets; source footer band;
  note primitives; legend in all four positions; structure independent of chart size (ADR 0007).
- `tests/lo`: label edit/hide/reset and focus through a dispatch, one undo step each, resize and
  reload from ODP and PPTX; source survives a reload; label name mapping after a copy.
- Manual: dialog text editing, checkbox lists for several series/categories and the look of muted
  charts (headless LibreOffice cannot drive modal dialogs, see AGENTS.md).

## Open questions

- Is the union rule (a point is focused if its series or its category is selected) what users expect,
  or should the dialog allow only one kind at a time? The union is the plan's default; if it feels
  confusing in use, the model can keep both sets but the UI can restrict editing to one.
- Do muted elements keep their patterns and markers? Probably yes, only the colour changes.
- Should a callout have a leader line to a picked label/segment in v1? The pick infrastructure
  exists, but the first version can ship text-only callouts.
- How is a long source line wrapped? `core/` has no text metrics; either truncate with an ellipsis
  or reserve two lines and rely on the renderer's wrap. Decide in the ADR.
- Does *Copy chart format* copy the font size? It is a format field, so yes; source and notes are
  chart content, so no. Implement `core/format.apply` accordingly.

## Out of scope

- Rich text, per-label fonts or colours, label templates per chart kind.
- Automatic label shrinking.
- Free-form drawing or connector editing on a chart.
- Animation and build steps (M31 research).
