# 0022. Agenda

- Status: accepted
- Date: 2026-10-29

## Context

M12 asks for an agenda: a slide that lists the chapters of a presentation and, before every
chapter, a copy of it with that chapter highlighted, kept in sync when the agenda changes. The M12
plan wanted to tie chapters to their first slides by slide names and to move the copies when
slides were moved. A spike against LibreOffice 26.8 showed that both fail:

- **Slide names do not survive PPTX**: after a round trip, slides are named after their title
  text. Shape names and document properties survive both ODP and PPTX.
- **There is no API to move a slide.** `XDrawPages` offers only `insertNewByIndex` and `remove`;
  `.uno:MovePage*` needs the slide sorter, which a hidden or headless document does not have.
  `XDrawPageDuplicator.duplicate` always puts the copy right after its original.
- `insertNewByIndex(i)` inserts *after* slide `i` (`-1` too, so nothing can go before the first
  slide). Inserting is not recorded for undo; removing is, unless recording is locked.

## Decision

- **Agenda slides are found by their list shape**, a text shape named `librecharts-agenda` on the
  *main slide* and `librecharts-agenda:<chapter id>` on a *divider*. Only exact names count: a
  slide the user duplicates gets a renamed list (` 1`) and is left alone.
- **A divider is where its chapter starts.** LibreCharts never moves slides. The user moves a
  chapter in the slide sorter, its divider with it; which slides belong to a chapter is simply
  what follows its divider.
- **Chapters are edited on the main slide**, one paragraph per chapter, and stored with their ids
  as JSON (`"v": 1`) in the document property `librecharts:agenda`, which `lo/store.py` excludes
  from the chart-id scan like the scheme. *Update agenda* reconciles the paragraphs with the stored
  chapters (`core/agenda.reconcile`): a title still present keeps its chapter, also when moved;
  the remaining titles take over the remaining chapters in order (renames); further titles are new
  chapters; the dividers of deleted chapters are removed. The chapter order is the list's order.
- **Commands**: *Insert agenda* adds a main slide ("Title Only" layout, the title "Agenda", a list
  of three placeholder chapters) after the current slide; after the main slide was deleted it
  lists the stored chapters again. *Start chapter here* first updates, then inserts a divider before
  the current slide for the chapter after the previous divider's one, or for a new chapter
  if that one already has a divider. Every command is refused, with a message, where it makes no
  sense: a second agenda, a chapter on an agenda slide or the first slide, an empty list.
- **Dividers are generated, not copied**: a new slide with the main slide's master page and
  layout, its title text and a list in the same place and font. The list is numbered
  (`1<tab>Title`, hanging indent); on a divider its chapter is bold in the *accent* (the palette
  colour with the highest contrast to the background, the text colour if none reaches 3:1) and the
  others are muted halfway to the background. Other shapes of the main slide are not repeated.
- **Undo**: a command is one explicit action (ARCHITECTURE.md, invariant 7) that re-applies the agenda as it was
  before or after it: the property, the agenda slides by role and page index
  (`core/agenda.changes`), and the main list's text as the user had typed it. Slides are matched
  by role, never by page objects, which do not come back once a slide is removed.
- **UI**: three entries in the LibreCharts menu and an Agenda section in the sidebar (*Start
  chapter here* and *Update agenda* need a stored agenda; *Start chapter here* is disabled on
  agenda slides).

## Alternatives considered

- **Slide names as anchors** (the plan): lost in PPTX.
- **Copies by `duplicate` plus moving**: no move API; the copies would pile up after the main slide.
- **Copying the main slide's shapes through the controller's transferable**: not tried. It needs
  the view and the transfer machinery that the clipboard uses, and clipboard tests abort
  LibreOffice in headless Linux (CI); generated dividers are fully testable.
- **Creating dividers for every chapter on update**: they would have to go somewhere (the end of the
  previous chapter) and the user would move them anyway; *Start chapter here* places them where
  they belong.
- **Chapters in a sidebar list or dialog**: typing on the slide is what users do with an agenda;
  dialogs cannot be tested headlessly.
- **A marker shape next to the current chapter instead of bold and colour**: more shapes to keep in
  place on every list size; bold and colour survive PPTX as plain text formatting.

## Consequences

- Without LibreCharts the agenda slides are plain slides with a text box; nothing breaks.
- Custom content on the main slide (pictures, notes) is not repeated on the dividers, and edits made
  on a divider are overwritten by the next update; both are documented in the changelog.
- A chapter cannot start on the first slide, and undoing the removal of a divider that the user
  had moved to the first slide puts it back as the second.
- If the property is lost (e.g. a tool that drops custom properties), the next update starts with
  new chapter ids; the old dividers are left untouched instead of being removed.
