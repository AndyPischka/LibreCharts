# M14: Annotations everywhere

Plan for the M14 milestone (ROADMAP 4.0 block): difference and CAGR arrows on line, Mekko, pie and
scatter charts; difference arrows between series, not only between categories; category gaps and
brackets over groups of categories.

## Goal

Every chart that shows comparable values can take the annotations that fit it, with the same
mechanics the column charts have since M4 (ADR 0010): placed by clicking, stored in
`ChartState.annotations`, one undo step each, surviving data edits, sorting, resizing and PPTX
round trips.

Already done, not repeated here: line charts draw difference/CAGR arrows, level arrows, axis
breaks and value lines (came with M7, `layout/line.py`); waterfall charts measure levels.

New in M14:

1. **Arrows on Mekko, pie and scatter charts.**
2. **Between-series arrows**: the two ends of a difference/CAGR arrow may belong to different
   series (one bar of series A vs. one bar of series B; a segment of one pie vs. a segment of
   another).
3. **Category gaps**: a widened gap between two adjacent categories that groups columns visually.
4. **Group brackets**: a bracket over a range of categories with a text label ("Phase 1", "H1").

Not in M14: axis breaks on the new kinds (Mekko/pie/scatter keep what they have), annotations on
area, butterfly and Gantt charts beyond what they have, and anything of M15-M17.

## Approach

### 1. Generalised arrow model (`core/model.py`, `core/state_io.py`)

An arrow measures two points, each a (category, series?) pair. Today `Annotation` has one optional
`series`; add a second one:

- `series_end: int | None = None` — the series the end category's value comes from. `None` keeps
  today's meaning (column total / line level / point). A between-series arrow has
  `start == end` (same category) and `series != series_end`.
- Validation changes from "an arrow needs two different categories" to "an arrow needs two
  different categories or two different series".
- `text: str = ""` — the label of a group bracket (below); empty draws the bracket without text.

New annotation kinds:

- `category_gap`: `start`/`end` are the two adjacent categories the gap opens between. Several
  gaps per chart are allowed (unlike an axis break). Drawable only while the two categories are
  adjacent in display order; a sorting or data edit that separates them hides it (stays stored).
- `group_bracket`: spans the categories `start..end` (inclusive), `series` is `None`, the label is
  `text`. Drawn in one lane per bracket, like arrow lanes.

Schema 12 → 13: migration adds `series_end` (old arrows: the value of `series`, so behaviour is
unchanged) and `text` (`""`). The new kinds exist only from 13 on.

`sorting.remap` moves the new kinds along like arrows (they are category-bound); `axis_break`
stays the only exception.

### 2. Measured values per chart kind (`core/annotations.py`)

`measured(state)` returns the `ChartData` an annotation measures. New views:

- **Mekko**: per series a segment's *level* (cumulative sum from the first series up to it, as
  `waterfall.levels` does for steps), per category the column total for `series=None`. Percent
  Mekko: levels and totals in percentage points.
- **Pie**: the segments' **shares of their pie in percent**, so an absolute difference reads as
  percentage points and a percent difference as relative change of shares. A pie's categories are
  the pies, its series the segments: a between-series arrow compares two segments (of one pie or
  of two).
- **Scatter**: unchanged (one y value per point); a CAGR's periods are the two points' x
  difference when positive, else their index distance.

`SUPPORTED` gains: `mekko: {difference, cagr}`, `pie: {difference, cagr}`, and `scatter`/`line`
keep their entries. Percent Mekko is the exception to the "no annotations on 100 % charts" rule in
`picking.supports`. `arrows()` must ignore the two new kinds (they are not arrows); `added()`,
`changed()` (now also `text=`) and `from_query` (now `series_end`, `text` and the new kinds)
extend accordingly.

### 3. Layout (`core/layout/`)

All lanes are counted from the annotations only, so the primitive structure stays independent of
the size (ADR 0007); every layout keeps raising `ValueError` when the box is too small.

- **`column.py` / `bar.py`**: anchors of an arrow end with a series already sit on that bar; for a
  between-series arrow with both ends in one category, the bracket style is only offered where
  the two bars have different x positions (clustered); stacked charts get the level style. A
  category gap adds a fixed `GAP_WIDTH` (1/100 mm) between the two slots; a group bracket spans
  the category centres in its own lane above the plot (column) / right of the outside labels
  (bar), with `text` above the bracket line.
- **`mekko.py`**: bracket lanes above the columns (above the width labels), level lanes right of
  the plot (before the series names); anchors on segment levels and column tops. The natural
  length per unit (`samescale`) respects the lanes.
- **`pie.py`**: bracket and level lanes as in the line layout, above and right of the pies;
  anchors at the segments' mid-angle points.
- **`scatter.py`**: bracket lanes above the plot, level lanes right of the rightmost point's
  label; anchors above the markers.
- Each layout gains a `*_at` hit test (`mekko_at`, `pie_at`, `scatter_at`) that returns the
  (category, series?) / point a click selected, like `column_at` and `line_at`.

### 4. Pick mode (`core/picking.py`, `lo/pick.py`)

- `target_at` wires the three new hit tests.
- `PickSession` records both series (`series`, `series_end`) instead of collapsing two equal
  series picks to `None`; it gains the kinds `gap` and `bracket` (two category picks, series
  ignored) next to `difference` and `cagr`. Prompts per kind ("click the first column to connect",
  ...) in `messages.py`, German and English.
- `lo/pick.py` is generic already and stays as it is.

### 5. UI (`core/menu.py`, `core/panel.py`, `core/messages.py`, `lo/`)

- Context menu and sidebar offer *Add gap* and *Add group bracket* on column and bar charts, and
  the arrows on Mekko, pie and scatter; per annotation: the existing switches plus *Change
  text...* for a group bracket. `annotation_title` names the new kinds and between-series arrows
  ("Difference Berlin vs. Munich", "Gap 2023/2024", "Phase 1 to Phase 3").
- The group bracket label is asked for after the picks, in a small modal dialog
  (`lo/textdialog.py`, built in code like `lo/axisdialog.py`; validation in core: non-empty, at
  most 80 characters). Modal dialogs cannot be driven by `test-lo`; the dialog is tested by hand.
- Every change is one `org.librecharts:` command with URL arguments and one undo step
  (`lo/chart.py`, `lo/undo.py` unchanged).

## Affected modules

| Layer | Module | Change |
|---|---|---|
| core | `model.py` | `series_end`, `text`, kinds `category_gap`, `group_bracket`, validation |
| core | `state_io.py` | schema 13 + migration, new fields in JSON |
| core | `annotations.py` | `SUPPORTED`, `measured` views, labels, `arrows` filter, queries |
| core | `sorting.py` | remap for the new kinds |
| core | `picking.py` | `target_at` for Mekko/pie/scatter, session kinds and series pairs |
| core | `layout/column.py`, `bar.py` | between-series anchors, gaps, group brackets |
| core | `layout/mekko.py`, `pie.py`, `scatter.py` | arrow lanes, anchors, `*_at` |
| core | `menu.py`, `panel.py`, `messages.py` | entries, titles, strings (de + en) |
| lo | `textdialog.py` (new), `commands.py` | bracket label dialog, commands |
| tests | `tests/`, `tests/lo/` | see test strategy |

Docs: new ADR 0024 (annotation model extension) after implementation; glossary terms
(*category gap*, *group bracket*, *segment level*, *percentage point*); ARCHITECTURE.md module
rows; CHANGELOG; ROADMAP status.

## Work packages

1. Model and schema: `model.py`, `state_io.py` (migration 12 → 13), `sorting.py`.
2. Annotation logic: `annotations.py` (`SUPPORTED`, `measured`, labels), `picking.py` sessions.
3. Layouts: column/bar (anchors, gaps, brackets), then Mekko, pie, scatter with their `*_at`.
4. UI: `menu.py`, `panel.py`, `messages.py`, `lo/textdialog.py`, `lo/commands.py`.
5. Integration: `tests/lo/` modules; docs (ADR, glossary, CHANGELOG, ROADMAP).

Each package ends with `uv run poe check` green; package 5 additionally with `uv run poe test-lo`.

## Test strategy

- **core** (`tests/`): validation and migration of the new fields; `measured` for Mekko (units
  and percent), pie and scatter; labels (percentage points on share charts, between-series);
  `PickSession` series pairs and the new kinds; `sorting.remap` for gaps and brackets; each
  layout: lanes reserved per annotation, gap width, bracket span, hit tests, and the same
  primitive structure at several sizes; menu/panel contents; every new string in English and
  German. Coverage of `core/` stays >= 90 %.
- **lo** (`tests/lo/`, real LibreOffice): placing each new annotation through the pick flow
  (`controller.select` inside the entered group as the stand-in for clicks), undo/redo of every
  new command, re-layout after a resize with gaps and brackets, PPTX round trip of a schema-13
  state, sorting that separates a gap. The group bracket dialog by hand (headless modal pitfall).

## Decisions

Agreed with the maintainer, 2026-11-03:

1. **Percent Mekko** takes difference arrows between segment levels, labelled in percentage
   points; no CAGR there (the column totals are all 100).
2. **Pie CAGR** compares the same segment's share across two pies; the periods come from the
   category names, as on column charts.
3. **Scatter CAGR** periods are the two points' x difference when positive, else their index
   distance.
4. **Category gaps** on column and bar charts only, not on line (suggests missing data) or Mekko
   (fixed column gaps already).
5. **Group brackets** stand above the plot in their own lane, not below the category names.
6. **Naming**: *group bracket* / German *Gruppenklammer*; *category gap* / *Kategorielücke*.

After implementation this plan is deleted; its lasting decisions move into ADR 0024.
