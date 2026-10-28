# 0004. Store chart state in a document property, anchored by the group name

- Status: accepted
- Date: 2026-10-28

## Context

A chart must stay editable after saving and reopening, as ODP and as PPTX (hard requirement:
consultants exchange PPTX). The chart on the slide is a group of native shapes (ADR 0002), so the data
and settings have to be stored next to it. Measured with LibreOffice 26.8 (group of two rectangles,
saved and reloaded, 1.2 KB payload):

| Location | ODP | PPTX |
|---|---|---|
| `UserDefinedAttributes` of a child shape | kept | **lost** |
| Group title / description (alt text) | kept | **lost** |
| Hidden text shape carrying the JSON | kept | kept, but **becomes visible** |
| Group name | kept | kept |
| Document custom property (95 KB tested) | kept | kept |

Groups have no `UserDefinedAttributes`. LibreOffice also renames pasted and duplicated shapes:
it cuts the trailing digits off the name and appends " 1", " 2", ... (`...f234` -> `...f 1`).

## Decision

- The group is named `librecharts:<chart-id>` (the *anchor*).
- The state (schema-versioned JSON, ADR 0006) is a document custom property with the same name.
- Chart ids are 12 hex characters ending in a letter, so a renamed copy still contains the whole id.
- `lo/store.claim` gives every chart exclusive ownership of its state before it is edited: a group
  whose name is not exactly an existing id (a renamed copy) or that shares its name with another group
  gets a new id and a copy of the state. Older ids are matched by unique prefix (at least 8 characters).
- A chart whose id has no stored state is *orphaned*: it still looks right (native shapes) but cannot be
  edited, and the user is told so.

## Alternatives considered

- **Child-shape attributes or alt text as primary storage**: lost in PPTX.
- **Hidden carrier shape**: becomes visible after a PPTX round trip.
- **Embedded Calc OLE object per chart**: heavy, odd in PowerPoint, and own settings would still need a home.

## Consequences

- Copies within a presentation (paste, duplicated slide) work and are independent after their first edit.
- Copying a chart into *another* presentation orphans it; the state does not travel. A redundant copy
  in a child shape's attributes (ODP only) is a possible later improvement.
- States of deleted charts stay in the document; cleaning them up on save is still to do.
- Renaming a group is not undoable; accepted, since the renamed copy is not usable otherwise.
