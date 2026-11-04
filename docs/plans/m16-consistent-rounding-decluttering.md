# M16: Consistent rounding and decluttering

Plan for the M16 milestone (ROADMAP 4.0 block): rounded labels that add up to the rounded
total, and labels that overlap move apart automatically (builds on M13, ADR 0023).

## Goal

1. **Consistent rounding.** Where value labels sum to a shown total, they are rounded so that
   they add up to that total: the segments of a stacked column or bar (and its total), the shares
   of a 100 % column, bar, percent Mekko and pie (which sum to 100 %). No more `33% + 33% + 33%`
   next to a total of `101%`, or `1.2 + 2.8` next to a total of `4.1`.
2. **Decluttering.** Labels that overlap move apart automatically, without a leader line
   (ADR 0023 rules one out: it would change the primitive structure):
   - a value label of a segment too small to hold it is no longer hidden but moves out of the
     segment and stacks with the column total (above a column, right of a bar end);
   - the labels of several line series at one category that overlap spread apart vertically;
   - overlapping outside labels of a pie spread apart vertically, per side of the pie.

Not in M16: leader lines, a generic overlap solver across all kinds (the three cases above are
the overlaps that occur in practice; each layout knows its own geometry), decluttering of series
names and axis labels (already spread by `common.spread`), anything of M17-M21. A moved label
(M13 offset) always wins over automatic placement.

## Approach

### 1. Consistent rounding (`core/rounding.py`, new)

Largest remainder rounding in the number format's own scale and precision, so the labels keep
the look of `format_value`/`format_share`:

- `consistent(values, total, fmt)` -> the label texts of the segments of one column: each value
  scaled by `fmt.magnitude`, rounded at `fmt.decimals` (the same default `format_value` draws:
  integral values without, others with two decimals) so that the rounded segments sum to the
  rounded total; the units go to the largest fractional remainders, ties to the earlier series.
- `consistent_shares(values, total, fmt)` -> the percentage texts of one column/pie, rounded at
  the share precision (`fmt.decimals`, else one decimal) so that they sum to exactly 100 %.
- `None` values keep the place of their label (no text); a single segment needs no adjustment.

### 2. Applying it (`core/layout/`)

- `column.py` / `bar.py`: `_stacked_column`/`_stacked_bar` label their segments and their total
  through `rounding.consistent`; `_percent_column`/`_percent_bar` label their shares through
  `consistent_shares` (the absolute total stays `format_value`).
- `mekko.py`: the percent variant labels its segment shares through `consistent_shares`.
- `pie.py`: the shares of each pie through `consistent_shares`.
- Unchanged: clustered, line, scatter, area (no total is shown), waterfall (step labels are
  changes, not parts of a shown sum), Gantt, Mekko width labels.

### 3. Decluttering (`core/layout/column.py`, `bar.py`, `line.py`, `pie.py`)

- **Flat segments** (`column.py`, `bar.py`, stacked and percent): the label of a segment below
  `MIN_SEGMENT_FOR_LABEL` is drawn at the column top (the bar end) in the stack of the total:
  the flat labels and the total are collected and moved apart with `common.spread`, plain text
  (no segment fill). The `hidden` flag stays `False` from now on; the primitive structure is
  unchanged (a label is always emitted, ADR 0007). In pick mode and for `labels.moved` (M13) a
  revealed label behaves like any keyed label.
- **Line labels** (`line.py`): the labels of one category are spread vertically with
  `common.spread` when they overlap (they keep their x, the lowest keeps its y).
- **Pie labels** (`pie.py`): the outside labels of one side (left/right half) that overlap are
  spread vertically like the line labels.

### 4. Model and schema

None: both features are computed at layout time, no `ChartState` field, no schema change, no
new command. Data edits, sorting, resizing, ODP/PPTX round trips and undo work as before.

## Test strategy

- `tests/core/test_rounding.py`: largest remainder with positive, negative and mixed values,
  magnitudes, decimals (fixed and default), shares summing to 100 %, ties, `None` values.
- `tests/core/test_layout_column.py` / `test_layout_bar.py`: segments sum to the total text
  (parsed back from the labels), flat labels are drawn above the column / right of the bar and
  no longer hidden, the total still sits above the spread stack.
- `tests/core/test_layout_line.py`, `test_layout_pie.py`, `test_layout_mekko.py`: overlapping
  labels move apart; shares sum to 100 %.
- `uv run poe check` green (the LO integration job is red on `main` already, see the
  `test_annotations` LibreOffice crash; not touched by M16, no `tests/lo` additions).

## Open questions

- None blocking; the reveal of flat labels replaces M13's "hidden" behaviour, which ADR 0023
  announced for M16 ("automatic placement and overlap removal will move labels out of segments").
