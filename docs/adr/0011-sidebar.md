# 0011. Sidebar: one deck with one panel that mirrors the commands

- Status: accepted
- Date: 2026-10-28

## Context

Menu and toolbar are hidden in the Notebookbar (ribbon) interface, and the context menu only shows
when a chart is selected. Users also want to see what is on a chart (its annotations) and remove
them without hunting for the arrow. The sidebar is the place for that in Impress.

## Decision

- `Sidebar.xcu` registers the deck `org.librecharts.deck` (icon: the difference arrow, context
  Impress) with one panel `org.librecharts.panel`; `Factories.xcu` registers the UI element
  factory `org.librecharts.PanelFactory` for `private:resource/toolpanel/org.librecharts/...`.
  `extension/entry.py` implements the factory and delegates to `lo/sidebar.py`.
- The panel is a plain window container with buttons and labels, created in code (no resource
  file). Its content is `core/panel.py`: pure data derived from the selected chart's state, tested
  without LibreOffice. Sections: insert chart, selected chart (status, edit data), add annotation,
  annotations on this chart (title, remove) and remove all.
- Every button dispatches an existing `org.librecharts:` command; the panel has no logic of its
  own. It redraws when its content differs from what it shows, on selection and document changes.

## Consequences

- Headless LibreOffice has no sidebar: `tests/lo/test_sidebar.py` checks the registration and
  builds the panel through the factory manager; layout and clicks are tested by hand.
- The layout uses pixel sizes and the sidebar's width; very narrow or high-DPI setups may need
  adjusting.
- Draw and Writer have no deck; only Impress, like the rest.
