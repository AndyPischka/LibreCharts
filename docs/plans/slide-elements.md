# Plan: M12 slide elements (Harvey balls, check marks, agenda, arranging shapes)

Status: draft, not yet agreed (2026-10-29). Builds on M9 (`core/geometry.py`).

## Goal

The small helpers of think-cell and empower that are not charts but appear on most consulting
slides:

- **Harvey balls**: a circle filled to 0, 25, 50, 75 or 100 %.
- **Check marks**: tick, cross or empty circle, e.g. in comparison tables.
- **Agenda**: an agenda slide and, before every chapter, a copy of it with the current chapter
  highlighted, kept in sync when the agenda changes.
- **Arranging shapes**: same width / height / size, arranging the selection into a grid with
  equal gaps, swapping the positions of two shapes. Impress already aligns and distributes; these
  are the missing pieces.

Non-goals: symbols inside table cells or running text (Impress tables cannot hold shapes; a
font-based solution would depend on installed fonts), stickers, sticky notes, a slide library.

## Approach

### Harvey balls and check marks (`core/elements.py`, `lo/elements.py`)

- An element is a group of native shapes like a chart (ADR 0002), but its whole state fits into the
  group name: `librecharts-element:harvey:50`, `librecharts-element:check:tick`. No document
  property, so copies and pasting into other decks just work and nothing needs forking.
- `core/elements.py`: parse and build names, and the primitives of an element: Harvey ball =
  outline circle (`Polygon` from `geometry.sector`, full circle) plus a filled sector; tick and
  cross = `Polyline`s; empty = outline circle. Colours from the document's scheme (M8): fill =
  palette entry 1, line = scheme line colour, tick green and cross red from new scheme fields
  (defaulting for old scheme files).
- Size: inserted at 0.6 cm; resizing keeps the aspect ratio through the resize watcher (it
  re-renders elements as squares centred in their new box).
- Changing: context menu of a selected element ("25 %", "50 %", ... / "Tick", "Cross", "Empty")
  and keyboard-friendly "Next state" (cycles), also for several selected elements at once, one
  undo step.
- Insert: menu, toolbar and sidebar ("Harvey ball", "Check mark"), inserted at the slide centre or
  next to the selected shape.

### Agenda (`core/agenda.py`, `lo/agenda.py`)

- State in a document property `librecharts:agenda` (JSON with version, like the scheme, ADR 0016):
  the list of chapters, each with its title and the **slide name** of its first slide; the agenda
  slides LibreCharts created, by slide name. Slides get stable names
  (`librecharts-agenda-<n>`) because Impress has no slide ids.
- "Insert agenda": an agenda slide with a numbered list (a text shape built from the chapters;
  three placeholder chapters at first) and the property.
- "Start chapter here" on a slide: adds a chapter whose first slide is this one and inserts a copy
  of the agenda slide before it with that chapter highlighted (bold, accent colour; the others in
  the scheme's grey).
- "Update agenda": rereads the chapter titles from the **main** agenda slide's text shape (one
  paragraph per chapter), rewrites every copy, adds or removes copies for added or removed
  chapters, and puts each copy in front of its chapter's first slide again if slides were moved.
- `core/agenda.py` computes what has to change (pure: from chapters and slide order to a list of
  inserts, removals, moves, texts); `lo/agenda.py` only executes it.
- Undo: inserting and removing slides through the API is not recorded either (as with shapes, to
  verify with a spike first); `lo/undo.py` gets an action that removes and re-inserts slides.

### Arranging shapes (`core/arrange.py`, `lo/arrange.py`)

- `core/arrange.py`: pure geometry on rectangles (x, y, w, h): `same_width`, `same_height`,
  `same_size` (to the largest selected shape), `grid(rects, columns, gap)` (keeps the top-left of
  the selection, row order by position), `swap(a, b)` (swaps centres, keeps sizes).
- `lo/arrange.py`: reads the selection, applies the result in one undo step. Charts in the
  selection are resized like any shape; the resize watcher re-lays them out (ADR 0007), and both
  must end up in the same undo step (to verify).
- "Arrange in grid..." asks for columns and gap in a small dialog; the rest needs no input.
- UI: a submenu "Arrange" in the LibreCharts menu and a sidebar section, enabled for two or more
  selected shapes (swap: exactly two).

## Affected modules

New `core/elements.py`, `core/agenda.py`, `core/arrange.py`; `core/geometry.py` (circle),
`core/style.py` (tick/cross colours, scheme version), `core/menu.py`, `core/panel.py`,
`core/messages.py`; new `lo/elements.py`, `lo/agenda.py`, `lo/arrange.py`; `lo/render.py` (render
elements), `lo/store.py` (element names), `lo/resize.py` (square elements), `lo/undo.py` (slide
actions), `lo/contextmenu.py`, `lo/sidebar.py`, `lo/commands.py`, `extension/entry.py`,
`extension/Addons.xcu`, `extension/images/`.

## Tests

- `tests/core`: element names round trip and invalid names; Harvey sector per level (0 % has no
  sector point list but the same structure); agenda diff for added, removed, renamed and moved
  chapters; arrange functions incl. grid with a partial last row and swap of different sizes.
- `tests/lo/test_elements.py`: insert, change state (one undo), copy and paste into another
  presentation, resize keeps a square, ODP and PPTX reload keep the name (PPTX: check that group
  names survive).
- `tests/lo/test_agenda.py`: insert agenda, start two chapters, rename one in the main agenda,
  update -> copies follow; move a chapter slide, update -> copy moves; one `.uno:Undo` per step.
- `tests/lo/test_arrange.py`: same size and grid on rectangles and a chart (chart re-laid out,
  one undo step).

## Docs

New ADRs "Slide elements" (state in the group name) and "Agenda" (slide names, property,
sync rules); ARCHITECTURE.md (new modules); glossary ("Slide element", "Harvey ball", "Check
mark", "Agenda", "Chapter", "Agenda copy"); CHANGELOG; ROADMAP; README.

## Open questions (recommendation first)

1. Element state in the group name (recommended) or in a document property like charts.
2. Agenda chapters edited on the main agenda slide's text (recommended) or in a dialog/list in
   the sidebar.
3. Highlight in agenda copies: bold and accent colour (recommended) or a marker shape next to the
   current chapter.
4. Arrange reference for "same size": the largest shape (recommended) or the first selected (UNO
   does not report the click order reliably).
5. Split M12 into two milestones (elements and arranging / agenda), since the agenda is the
   largest single piece and independent of the rest.
