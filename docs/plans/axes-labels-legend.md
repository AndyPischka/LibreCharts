# Plan: M6 axes, labels and legend

Status: draft, not yet agreed (2026-10-29). Builds on M5 (`docs/plans/chart-options.md`).

## Goal

Charts get the formatting think-cell and empower offer beyond direct value labels:

- an optional **value axis** with tick labels and optional **gridlines**,
- **number formats**: decimals, magnitude (thousands, millions, billions) and a unit suffix,
  with the decimal separator of the chart's language,
- a way to tell the series apart on column, bar and waterfall charts: **series labels** right of
  the last column (think-cell style) or a **legend**,
- **value lines** (a target value or the average) across the plot,
- **label contrast**: white text on dark segments.

Defaults keep today's look: no axis, no gridlines, automatic decimals. Existing charts do not
change when the document is opened.

Non-goals: free positioning of single labels (see open question 5), fonts and colours (M8), axis
titles.

## Approach

### State (`core/model.py`, `core/state_io.py`)

- New frozen dataclass `Format`, field `ChartState.format: Format = Format()`:
  - `axis: bool = False`, `gridlines: bool = False` (only drawn with `axis`),
  - `series_names: Literal["none", "labels", "legend"]`,
  - `decimals: int | None = None` (`None`: today's rule, at most two), 0..4,
  - `magnitude: Literal[0, 3, 6, 9] = 0` (power of ten the values are divided by),
  - `unit: str = ""` (suffix such as `€` or `%`, at most 10 characters),
  - `separator: Literal[".", ","]`, set from the UI locale when the chart is inserted.
- `Format` is the unit that M8 copies between charts ("copy chart format").
- New annotation kind `value_line` with a new field `Annotation.value: float | None`
  (`None`: the average of the column sums). Like the axis break it belongs to the axis
  (`start == end == 0`).
- Schema version 6; migration `_v5_to_v6` adds `format` with `series_names = "none"`,
  `separator = "."` (today's output), and `"value": null` to every annotation.

### Layout

- `format_value(value, fmt)` in `layout/common.py` applies decimals, magnitude, unit and
  separator; every layout passes `state.format` through. Percent labels (Mekko, 100 %) use the
  decimals and the separator, not the magnitude.
- Value axis: a band left of the plot (below it for bar charts) with one `Text` per tick of
  `Axis.ticks()` and a new `LineRole` `"axis"`. The tick count comes from `nice_axis`, i.e. from the
  data, never from the size (ADR 0007). With an axis break, ticks inside the removed range are
  left out and the axis line gets the break mark.
- Gridlines: one `Line` per tick across the plot, new role `"grid"` (light grey in the renderer),
  emitted before the columns so they lie behind them.
- Series labels: a band right of the last column, one `Text` (role `"series"`) per series, level
  with its segment of the last column (the Mekko already does this; the code moves to `common.py`).
  Legend: a band above the plot with a small `Rect` swatch and a `Text` per series.
- Value lines: a dashed `Line` across the plot at the value and a label right of it, in the lane
  area used by level arrows (`LEVEL_LANE_WIDTH`).
- Label contrast: `Text` gets `fill: int | None`, the series of the rectangle behind it.
  `core/style.py` (new, pure) decides `text_color(fill_rgb)` by relative luminance; `render.py`
  uses it. The palette moves from `render.py` to `core/style.py` for that (M8 extends this module).

### Commands and UI

- `ChangeFormat?axis=true|false`, `gridlines=...`, `series_names=none|labels|legend`: parsed in
  new `core/format.py`, applied through `chart.redraw` (one undo step).
- `NumberFormat`: a modal dialog (`lo/formatdialog.py`, built like `lo/axisdialog.py`) with
  decimals, magnitude, unit and separator; parsing and validation of its input in `core/format.py`.
- `ValueLine`: a dialog with "Value" or "Average"; changeable later from the annotation list
  (like the axis break).
- Context menu: a submenu "Format" / "Format" with the axis, gridline and series-name switches
  and "Number format..." / "Zahlenformat...". "Add value line..." joins the annotation commands.
- Sidebar: a "Format" section with the same entries.
- Which chart kinds get what: axis and gridlines on column, bar, waterfall and units Mekko;
  series names on column, bar and Mekko; value lines on column, bar and waterfall.

## Affected modules

`core/model.py`, `core/state_io.py`, new `core/format.py`, new `core/style.py`,
`core/primitives.py` (roles, `Text.fill`), `core/layout/common.py`, all layouts in `core/layout/`,
`core/annotations.py`, `core/axis_break.py` (ticks around a break), `core/menu.py`,
`core/panel.py`, `core/messages.py`, `lo/render.py`, new `lo/formatdialog.py`, `lo/commands.py`,
`lo/sidebar.py`, `extension/entry.py`.

## Tests

- `tests/core`: migration v5 -> v6 (old charts keep their look: same primitives as before);
  `format_value` for decimals, magnitude, unit, separator; axis ticks with and without break;
  gridlines behind columns; series labels and legend; value line at a value and at the average;
  structure independent of size for every new element; contrast colour per palette entry;
  dialog input validation.
- `tests/lo/test_format.py`: `ChangeFormat` switches shapes and undoes in one step; format and
  value lines survive ODP and PPTX reload and data sheet edits; label text colour on a dark
  segment is white. The dialogs are tested by hand (headless `execute()` returns at once).

## Docs

New ADR "Chart format" (state, defaults, why the separator is stored); ARCHITECTURE.md
(`format.py`, `style.py`, `formatdialog.py`); glossary ("Value axis", "Value line",
"Series labels", "Legend", "Magnitude"); CHANGELOG; ROADMAP; README.

## Open questions (recommendation first)

1. Decimal separator stored per chart (recommended: a German deck stays German on an English
   machine) or taken from the current UI locale at every layout.
2. Series names on newly inserted stacked charts: "labels" (recommended, think-cell style), on
   clustered: "legend"; existing charts keep "none".
3. Magnitude suffix: localized ("Tsd.", "Mio.", "Mrd." / "k", "M", "bn", recommended) or left to
   the unit field.
4. Value line "average": of the column sums (recommended) or per series.
5. Moving single labels by hand: not in M6 (recommended). Offsets would have to be stored per
   label and survive data edits, sorting and resizing; move it to 3.0.
