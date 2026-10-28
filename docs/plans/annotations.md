# Plan: annotations (M4)

Status: agreed (open questions answered as recommended); step 1 (spike) done, see below.

## Spike results (LibreOffice 26.8, Windows)

- Info bar (`appendInfobar`/`updateInfobar`/`removeInfobar` on the controller) and key handler
  (`addKeyHandler`, `Esc` swallowed) work.
- Context menu interceptor is called on right-click and Shift+F10; `event.Selection` is the chart
  group, so the menu cannot tell which column was clicked. Adding entries needs
  `uno.invoke(container, "insertByIndex", (i, uno.Any("com.sun.star.beans.XPropertySet", t)))`.
- **Pixel -> document mapping is unreliable**: mouse handler coordinates are relative to the inner
  edit window, and `controller.VisibleArea` does not match its size (x and y scale differ in
  headless mode). Robot clicks via `helpers.click` land only roughly where intended.
- Instead, **LibreOffice hit-tests for us**: `.uno:EnterGroup` on the chart, then a click (or
  `controller.select(child)`) selects the child under the mouse and a selection change listener
  sees it; `.uno:LeaveGroup` selects the group again. Works in hidden documents, so the pick flow
  can be tested on headless Linux by selecting children.
- Impress has no mouse motion handler, so a drag in pick mode cannot be blocked: dragging a bar
  moves it until the annotation redraw replaces the children.

Consequences for the design: pick mode enters the chart group and listens for selection changes;
the picked child's box centre is hit-tested in core. The context menu does not pre-pick the start
column; it starts pick mode and lists the existing annotations (submenu per annotation:
percent/absolute, bracket/level, remove), so no hit-test of annotations is needed.

## Goal

Column charts (stacked and clustered) get three annotations, placed by clicking in the chart:

- **Difference arrow** between two columns, in two styles:
  - *bracket*: up from column A, across, arrow down onto column B, label in the middle;
  - *level*: dashed helper lines at the heights of A and B, vertical arrow right of the plot.
  The label shows the relative difference ("+25%") by default and can be switched to absolute ("+5").
- **CAGR arrow** between two columns: bracket like above, label is the compound annual growth rate.
- **Axis break** in one column: the column is shortened, a break mark crosses it, its label keeps the
  real value.

Bar, waterfall and Mekko charts follow later (bar and waterfall), or never (Mekko). Total labels
already exist for stacked columns; M4 adds nothing there.

## Interaction

1. Select a chart. Choose *Difference arrow*, *Level difference*, *CAGR arrow* or *Axis break* from the
   LibreCharts toolbar or menu, or from the context menu of the selected chart.
2. **Pick mode**: the chart group is entered (the rest of the slide is dimmed) and an info bar says
   what to click ("Click the start column", then "Click the target column"; axis break: one click).
   `Esc`, the info bar's close button, or a click outside the chart cancels.
3. After the last click the group is left, the annotation stored and the chart redrawn and
   selected: one undo step.
4. The context menu of a selected chart lists its annotations ("Difference 2023 -> 2025"), each
   with *Show percent / Show absolute*, *Bracket / Level* (difference arrows) and *Remove*.

Double-click keeps opening the data sheet.

Every action is a command `org.librecharts:<Name>?<args>` (e.g. `AddAnnotation?kind=difference&from=0&to=2`).
The context menu dispatches these, and tests use them on headless Linux, where clicks cannot run.

## Design

### State (schema v2)

`ChartState.annotations: tuple[Annotation, ...]`, a frozen dataclass:

| Field | Values |
|---|---|
| `kind` | `difference`, `cagr`, `axis_break` |
| `start`, `end` | category indices (`axis_break`: `start` only, `end == start`) |
| `series` | `None` = column total (stacked); series index for a bar of a clustered chart |
| `style` | `bracket`, `level` (difference only) |
| `label` | `percent`, `absolute` (difference only) |

Migration v1 -> v2 adds `"annotations": []`. Annotations point to category **indices**. An
annotation whose indices no longer exist after a data sheet edit is kept in the state but not drawn,
so undoing the edit brings it back.

### Core (no UNO)

- `core/annotations.py`: the `Annotation` model; difference and CAGR values and their label text.
  CAGR periods: if both category names are whole numbers (years), their difference, otherwise
  `end - start`. A start value of 0 (percent) or a non-positive one (CAGR) gives the label "–".
- `core/layout/column.py`: one *lane* per bracket in the band above the plot, one band right of the
  plot if any level arrow exists. Axis break: the scale ignores the broken column, which is drawn
  at 1.15 x the next-tallest column and crossed by a break mark. Lanes and bands depend on the
  annotations only, never on the size (ADR 0007).
- `core/primitives.py`: `Line` gets `arrow: bool` (end arrowhead) and roles `annotation` and
  `helper` (dashed); break marks are two short parallel lines.
- `core/hittest.py`: chart-relative point (centre of the picked child) -> `(category, series)`,
  computed from the same layout. `PickSession`: a small state machine (needed picks, collected
  picks, cancel), fully unit-tested.

### Adapter

- `lo/pick.py`: starts and ends sessions: enters the group, listens for selection changes, shows
  the info bar (`XInfobarProvider`), cancels on `Esc` (`XKeyHandler`) or when the selection leaves
  the chart. `lo/doubleclick.py` stays as it is.
- `lo/contextmenu.py`: `XContextMenuInterceptor` that adds entries when the selection is a chart.
- `lo/chart.py`: `add_annotation`, `change_annotation`, `remove_annotation`; each one undo step.
- `lo/render.py`: arrowheads (`LineEndName`), dashed helper lines.
- `extension/`: toolbar buttons and icons, menu entries, `entry.py` routes the new commands. All
  strings in German and English.

## Steps (one or more commits each, `check` and `test-lo` green after each)

1. **Spike** (throwaway, on 25.8 and 26.8): context menu interceptor in Impress, info bar, key
   handler, pixel -> document mapping of a click. If one fails, fallback: no context menu (toolbar
   only) / status bar text instead of the info bar.
2. Core: `Annotation`, schema v2 and migration.
3. Core + adapter: bracket difference arrow, `AddAnnotation` command, rendering, undo, persistence.
4. Pick mode with clicks, toolbar and menu entries.
5. Context menu: add from a column; percent/absolute, style switch, remove.
6. Level difference arrow.
7. CAGR arrow.
8. Axis break.
9. Docs: ADR 0010 (annotations: state, interaction, index references), glossary (lane, pick
   mode), ARCHITECTURE, README, CHANGELOG, ROADMAP; delete this plan.

## Tests

- Core: model and migration, values and labels (incl. "–" cases, year periods), layout per
  annotation (geometry, structure independent of size), hit-testing, `PickSession`.
- `tests/lo`, also on headless Linux: add/change/remove via dispatch with arguments; one undo step
  each; survives ODP and PPTX round trip; copies keep their annotations; resize keeps them in place.
- `tests/lo`, also on headless Linux: pick mode driven by `controller.select(child)` in a hidden
  document; selecting something outside the chart cancels.
- `tests/lo`, Windows only (`skip_on_headless_linux`): `Esc` via the Toolkit robot cancels.

## Open questions (with recommendation)

1. Axis break height: automatic, 1.15 x the next-tallest column? (Recommended: yes, no setting.)
2. CAGR periods from year names, otherwise the column distance? (Recommended: yes.)
3. Labels stay locale-neutral ("+25.5%") like the existing value labels; German number format
   ("+25,5 %") as a separate later change for all labels? (Recommended: yes.)
4. Stacked charts: difference between column totals only, not between single segments?
   (Recommended: yes for M4.)
