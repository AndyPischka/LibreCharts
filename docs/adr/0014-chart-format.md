# 0014. Chart format: axes, number formats, series names and value lines

- Status: accepted
- Date: 2026-10-29

## Context

After M5 a chart can change its variant, but its look is fixed: no value axis, no way to set
decimals, a magnitude or a unit, and no way to tell the series apart on a column or bar chart
beyond the colours. think-cell and empower charts offer all of that per chart. Existing charts must
keep their exact look when a document is opened, and the format must survive data edits, copies and
ODP/PPTX files like every other part of the chart state.

## Decision

Agreed with the maintainer in `docs/plans/axes-labels-legend.md`:

- **State**: new frozen dataclass `Format`, field `ChartState.format`. Fields:
  `axis: bool = False`, `gridlines: bool = False` (drawn only with an axis),
  `series_names: "none" | "labels" | "legend"`, `decimals: int | None` (`None`: today's rule, at
  most two; 0..4), `magnitude: 0 | 3 | 6 | 9` (power of ten the values are divided by),
  `unit: str` (suffix such as `€` or `%`, at most 10 characters), `separator: "." | ","` and
  `language: str` (two-letter code). `Format` is the unit M8 copies between charts.
- **Why the separator and the language are stored**: the layout is locale-free. The chart keeps the
  separator and the magnitude words of the deck it was made in, also on a machine with another UI
  locale. `lo/chart._insert` applies `format.default_format(kind, grouping, locale)`; the locale
  comes from `ui.ui_locale` in `commands._insert`.
- **Defaults**: new charts keep today's look (no axis, no gridlines, automatic decimals) but name
  their series the think-cell way: `labels` for stacked column/bar and Mekko charts, `legend` for
  clustered ones, `none` for waterfall charts. `Format()` itself stays all-defaults, so a chart
  without a stored format (a test) looks as before.
- **Schema version 6**: `_v5_to_v6` adds `format` and `"value": null` to every annotation. Existing
  charts get `series_names = "labels"` on a Mekko (which always showed them right of the plot) and
  `"none"` on column, bar and waterfall charts; `separator = "."`, `language = "en"` keep the old
  output byte for byte.
- **Value lines**: new annotation kind `value_line` with the new field `Annotation.value`
  (`None`: the average). Like the axis break it belongs to the axis (`start == end == 0`). A chart
  may have several. The average is the mean of the column sums; on a waterfall it is the mean of
  the levels the steps end at.
- **Layout**: `layout/common.py` gains `format_value` (decimals, magnitude, unit, separator),
  `format_share` (decimals and separator, never the magnitude, for percent labels),
  `visible_ticks` (ticks outside an axis break) and the shared series-label/legend drawing. The
  layouts take `fmt: Format`; the primitive roles `"axis"` and `"grid"` and `Text.fill` (the series
  colour behind a label) are new.
- **Axis**: column, bar, waterfall and units-Mekko charts can show one. A 100 % column or bar chart
  uses the fixed 0..100 scale. A percent Mekko has no value axis. Gridlines are one line per tick
  behind the segments.
- **Contrast**: `core/style.py` (new, pure) holds the series palette and decides black or white
  text by WCAG relative luminance (threshold 0.5). The palette moves there from `lo/render.py`.
- **Commands and UI**: `ChangeFormat?axis=...`, `gridlines=...` and `series_names=...` take exactly
  one option per call and are applied through `chart.redraw` (one undo step each). `NumberFormat`
  and `ValueLine` open modal dialogs (`lo/formatdialog.py`, built like `lo/axisdialog.py`); their
  input is validated in `core/format.py` and `core/value_line.py`. The context menu gets a "Format"
  submenu and "Add value line..."; the sidebar gets a Format section and a value-line button.
  Existing value lines are edited from the annotation list.

## Alternatives considered

- **Decimal separator from the current UI locale at every layout**: a German deck would switch to
  dots when opened on an English machine, and the same document would look different per user.
- **A localized magnitude suffix chosen at layout time**: the same problem; storing `language`
  keeps "Tsd./Mio./Mrd." in a German deck and "k/M/bn" in an English one.
- **Series names as two booleans (`labels`, `legend`)**: both at once makes no sense and would have
  to be validated everywhere; one enum is the same rule as `grouping`.
- **One value line per chart**: users compare against a target and an average at the same time; the
  lanes already stack annotations.
- **Axis on a percent Mekko**: its columns are equal height by definition; an axis would add no
  information.
- **Contrast by a fixed rule per palette index**: any later colour scheme (M8) would break it;
  luminance works for every fill.

## Consequences

- A document saved with schema 6 cannot be read by older builds ("saved by a newer LibreCharts");
  the shapes still display.
- The axis and gridlines are part of the layout, so they follow resize and the "same primitive
  structure for every size" rule (ADR 0007).
- `Format` is the transferable unit for "copy chart format" in M8, and `core/style.py` the place
  where colour schemes will plug in.
- The number-format and value-line dialogs cannot be driven by `test-lo` (headless `execute()`
  returns at once); their logic is tested in `tests/core`, the dialogs by hand.
