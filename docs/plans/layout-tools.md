# M26: Layout tools, process graphics and icons

- Status: proposed
- Milestone: M26 (6.0)
- Builds on: M12 (arrange, ADR 0021), M19 (corporate design check, ADR 0029), M13 (resize watcher)
- Decision: new ADR for the graphics state in the group name and the icon set

## Goal

Everyday slide work still needs LibreOffice's own alignment dialogs, and the extension has no
process, pyramid or chevron graphics. M26 makes the Arrange commands complete and adds a small,
consistent set of slide graphics that follow the colour scheme, resize cleanly and need no external
assets.

## Scope

### Arrange commands

Extend `core/arrange.py`; the geometry stays pure and unit-tested.

- **Distribute horizontally / vertically**: keep the first and last shape, make the gaps between
  adjacent shapes equal. A second mode distributes the centres equally; both are one command with an
  axis and a mode argument.
- **Align edges**: left, right, top, bottom, horizontal centre, vertical centre. The anchor is the
  selection's bounding box.
- **Align to slide**: the same six alignments against the slide edges, with an optional margin in
  1/100 mm. The corporate design margins (M19) can become the default margin later.
- **Equal size** exists; add **same gap** as a special case of distribute? No, distribute already
  covers it. Keep the command set small.
- Commands are `Arrange?op=distribute&axis=h&mode=gaps`, `Arrange?op=align&edge=left`,
  `Arrange?op=align-slide&edge=top&margin=500`. A command with fewer than two selected shapes is a
  no-op with a message, like the existing Arrange commands.
- Undo: one explicit action per command (`lo/undo.py`), exactly like M12.

### Process, pyramid and chevron graphics

- New slide elements, inserted from the menu, toolbar and sidebar:
  - **Process**: a row of rectangular steps with arrows between them.
  - **Chevron**: a row of chevron-shaped polygons that interlock.
  - **Pyramid**: stacked trapezoids, widest at the bottom.
- Inserted with four steps and placeholder text (*Step 1* ...). The text is a child text shape and is
  edited in place with Impress's normal text editing; no dialog is needed to change a label.
- The group name stores the variant and orientation:
  `librecharts-graphic:process:4:horizontal`, `...:chevron:4:horizontal`,
  `...:pyramid:4:vertical`. A copy gets the usual ` 1` suffix (see `lo/store.py`). Step labels are
  the child text shapes in reading order, so no document property is needed.
- Context menu: *Add step*, *Remove last step*, *Switch direction* (horizontal/vertical), *Change
  colour*? Colours come from the scheme; a per-graphic palette override is a later option.
- Resize: `lo/resize.py` re-lays the graphic out from its group name and the current size, reading
  the child texts in order. The primitive structure is independent of size (ADR 0007).
- Adding/removing a step keeps the existing labels for the remaining steps and gives a new step the
  next placeholder. One undo step per command. The operation is simpler than the agenda's
  reconcile: the graphic owns its text shapes.

### Icon set

- A small built-in set of simple monochrome vector icons drawn from primitives (no bundled images,
  no licence question): arrow right, arrow up, target, warning, check, cross, idea, person, gear,
  calendar, money, chart.
- Insert at 1 cm square at the current selection or slide centre; resize freely, the icon scales
  its line width proportionally? Keep the line width fixed like chart shapes; a 1 cm icon and a
  4 cm icon both look right.
- Colour comes from the scheme's line colour, so a corporate scheme applies. The group name is
  `librecharts-graphic:icon:<name>`; the resize watcher regenerates the primitives at the new size.
- Icons are not meant to be a full icon library. If users need logos or pictograms, they insert a
  picture; a documented import path for SVG/PNG is out of scope.

## Data model

- No `ChartState` change. Graphics are slide elements whose state is the group name plus child text
  shapes, like Harvey balls and check marks (ADR 0021).
- `core/graphics.py`:
  - `Graphic` dataclass: `kind: Literal["process", "chevron", "pyramid", "icon"]`, `steps: int`,
    `horizontal: bool`, `icon: str`.
  - `name(graphic)`, `parse(group_name)`, validation of step counts (1..8) and icon names.
  - `layout(graphic, width, height, labels)` -> `tuple[Primitive, ...]` with the text primitives
    carrying the labels. The renderer creates one text shape per label, so direct editing works.
- `core/icons.py`: icon names and a function `primitives(name, width, height)`.
- No schema bump; no state in document properties.

## Approach

1. **Arrange math and tests.** Add the functions to `core/arrange.py` and the command parsing to
   `lo/arrange.py`. Extend `core/menu.arrange_items` and the sidebar `_ARRANGE_ICONS` with the new
   operations. The existing selection handling and undo action are reused.
2. **Graphics core.** Write `core/graphics.py` and `core/icons.py` with pure geometry, then a
   `lo/graphics.py` that inserts groups, reads child labels, re-renders on resize and handles
   add/remove/direction. Follow `lo/elements.py` as the template (find, insert, change, fit).
3. **Resize integration.** Extend `lo/resize.py` to collect graphics like elements and call
   `fit_to_size`. Read child text in one pass (AGENTS.md pitfall: proxies read later can return
   default geometry).
4. **UI.** Menu and toolbar entries for the three process variants and the icon submenu; sidebar
   buttons with icons. Context menu for a selected graphic. Texts in `core/messages.py`, then
   `uv run poe locales`.
5. **Docs and help.** A short section in the README and the extension description; the data sheet is
   not involved, so the help text is one paragraph per graphic.

## Affected modules

| Module | Change |
|---|---|
| `core/arrange.py` | Distribute, align, align-to-slide |
| `core/graphics.py` | New: group names, validation, geometry |
| `core/icons.py` | New: icon primitives |
| `core/menu.py` | Arrange entries, insert graphics, context menu |
| `core/panel.py` | Arrange icons/buttons, graphics insert buttons |
| `core/messages.py` | UI strings in English and German |
| `lo/arrange.py` | Command parsing and undo |
| `lo/graphics.py` | New: find, insert, edit, fit, undo |
| `lo/resize.py` | Re-layout graphics on resize |
| `lo/commands.py` | Dispatch commands |
| `extension/Addons.xcu`, `extension/images/` | Menu/toolbar entries and icons |
| `extension/description/` | Feature list |

## Tests

- `tests/core/test_arrange.py`: distribute gaps and centres with unequal widths, two and many
  shapes, align each edge, align to slide with and without margin, no-op for one shape, negative
  coordinates.
- `tests/core/test_graphics.py`: name/parse round-trip, step limits, icon names, geometry for 1..8
  steps, text primitives in reading order, structure independent of size.
- `tests/core/test_icons.py`: every icon name returns primitives inside the box; unknown names are
  rejected.
- `tests/lo`: insert each graphic, edit text, add/remove step, switch direction, undo, resize,
  reload ODP/PPTX, copy/paste (name suffix), arrange commands on a multiple selection including a
  chart.
- Manual: look of the graphics in the corporate scheme; text editing in place.

## Open questions

- Should graphics be one group or an Impress "custom shape" with a text child? A group is consistent
  with the existing chart/element model and survives ODP/PPTX; custom shapes lose their text on some
  filter paths.
- Add step above/below for a vertical pyramid, or only append/remove at the end? Start with end
  only; inserting in the middle is a later command.
- Arrow style between process steps: a separate arrow shape or a chevron-like notch in the
  rectangles? A notch keeps it one primitive per step and resizes cleanly.
- Icon colour: scheme line colour or a palette entry per icon? Scheme only in v1; a per-icon colour
  command can reuse the series colour mechanism later.
- Align to slide margins: use zero margin or the M19 corporate margins when a scheme is loaded?
  Offer a margin argument and let the UI pass the scheme margin when available.
- Distribution should keep the order of shapes by position, not selection order. The existing grid
  sorts by `(y, x)`; reuse that rule.

## Out of scope

- Smart guides, snapping or a live layout preview while dragging (Impress's own guides remain).
- Custom shapes, org charts, timelines (Gantt covers timelines).
- An external icon library or SVG import.
- Animations for process steps.
