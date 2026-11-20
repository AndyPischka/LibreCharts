# 0041. Two sidebar decks: charts and presentation

- Status: accepted
- Date: 2026-11-20
- Amends: [0011](0011-sidebar.md)

## Context

The single sidebar panel grew with every milestone (insert, chart, format, elements, arrange,
agenda, annotations, document, design). It no longer fits a sidebar and the user scrolled past
sections that belonged to a different task.

## Decision

- Two decks with one panel each, both created by the same factory (`org.librecharts`) and
  `lo/sidebar.py`; the last part of the resource URL picks the content:
  - **LibreCharts** (`org.librecharts.deck`, `.../Panel`, difference icon): *Insert chart*, the
    selected chart (data, link, options, *Format*) and its annotations (add, list, remove all).
    Everything that works on a chart.
  - **LibreCharts Presentation** (`org.librecharts.deck.presentation`, `.../Presentation`,
    align icon): *Elements* (Harvey balls, graphics, icons), *Arrange*, *Agenda* and *Document*
    (update links, colour scheme, templates, design check). Everything that works on shapes and
    the whole deck.
- `core/panel.py` stays one `Panel` value; each panel draws its part of it.

## Consequences

- Each panel is about half as high; both still scroll when the sidebar is small.
- A new button goes into the panel whose task it belongs to; the sections of ADR 0011 keep their
  names.
- Both panels watch the selection and the document, so each redraws on every change of the shared
  content, also when its own part is unchanged.
