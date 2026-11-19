# 0029. Corporate design check

- Status: accepted
- Date: 2026-11-19

## Context

M8 gave every document a colour scheme and let a corporate design be loaded from a scheme file
(ADR 0016). That keeps the charts consistent, but a deck also holds text boxes, shapes and
pictures that people format by hand, and charts that sit wherever they were dropped. M19 asks for a
check of a whole presentation against the corporate design file (colours, fonts, positions) and a
fix of every deviation in one step.

## Decision

- **The corporate design file is the scheme file of M8** with an optional `check` object:
  `colors` (more allowed colours, integers like the palette), `fonts` (more allowed font names) and
  `margins_mm` (`left`, `top`, `right`, `bottom`). Scheme readers ignore `check`, so the same file
  still loads as a scheme. `core/designcheck.py` parses it into `Rules`; a malformed file raises
  `DesignError`. The version stays `"v": 1`: the scheme part is unchanged and older builds simply
  ignore the new object.
- **Allowed colours** are the palette, text, line and background colours of the scheme plus
  `check.colors`; **allowed fonts** the scheme's font plus `check.fonts` (case-insensitive). A shape
  with a solid fill, a visible line or text portions in another colour or font deviates. Automatic
  text colours, pictures, OLE objects, media and tables are not judged by colour.
- **Charts are checked as a whole.** Their shapes take colour and font from the document's scheme,
  so a chart deviates when the document's scheme looks different from the corporate one (the
  scheme's name does not count). That is one finding for the whole document, shown only when the
  presentation has a chart. Harvey balls and check marks keep their fixed colours; plain groups
  are entered for colours and fonts.
- **Positions**: with margins, every top-level shape must lie inside the slide area within them.
  Charts are measured by their frame (ADR 0023). The fix moves a shape inside, and shrinks it with
  its aspect ratio if it is too large; a resized chart is laid out again (`chart.fit_to_size`).
- **Fixes**: a deviating colour becomes the allowed colour closest to it (the "redmean" weighted RGB
  distance), a deviating font the scheme's font; text attributes are written through a text cursor
  over each portion. A scheme deviation is fixed by switching the document's scheme, which redraws
  every chart. All of it is **one undo step**: LibreOffice's recording is locked and one explicit
  action restores the old values, the old positions and the old scheme.
- **Surfaces**: the command `org.librecharts:CheckDesign` (menu, sidebar *Document* section) asks
  for the file, shows the report and asks whether to fix. `file=<url>` skips the picker,
  `fix=true` fixes without asking and `fix=false` only reports (macros, tests). `api.check_design`
  serves Python scripts, and the command line gets `check DECK --design FILE [--fix] [--out]`: exit
  code 3 when deviations were found and not fixed.

## Alternatives considered

- **A separate corporate design format**: two files describing one design would drift apart; the
  scheme file already is the corporate design of M8.
- **Checking every shape of a chart**: they follow the scheme by construction; a finding per bar
  would bury the one that matters (the document's scheme).
- **Fixing colours to the first palette colour**: the closest allowed colour keeps the intent of
  the original (a dark blue stays a dark blue).
- **Snapping positions to a layout grid**: needs a grid definition nobody has yet; margins cover the
  common rule ("nothing outside the content area") and a grid can be added to `check` later.
- **LibreOffice's own undo recording of property changes**: it is partial for API writes; an
  explicit action is what every other chart operation does (ADR 0006 and `lo/undo.py`).

## Consequences

- A corporate design team can hand out one JSON file that styles charts (Load scheme) and checks
  decks (Check corporate design), interactively and in a build pipeline (`poe deck check`).
- Master slides and layouts are not checked: they belong to the template, which the corporate
  design team owns. Theme colours that LibreOffice resolves to plain RGB values are checked by
  their RGB value.
- Shapes that have no allowed counterpart (photos, logos in odd colours) are left alone, because
  only fills, lines and text are judged; a logo drawn as shapes must have its colours in
  `check.colors`.
