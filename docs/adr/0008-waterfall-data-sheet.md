# 0008. Waterfall data sheet: a value row and a "Total" marker row

- Status: accepted
- Date: 2026-10-28

## Context

A waterfall chart shows changes (steps) between a start and an end value and often subtotals in
between. The data sheet must say which columns are totals. Column and bar charts use one row per
series, which does not fit: a waterfall has exactly one series of changes.

## Decision

Fixed rows, parsed by `core/waterfall.py`:

- row 1: category names; row 2: values; row 3: marker row. Any entry other than empty, `0`, `false`,
  `no`, `nein` or `n` makes the column a *total*. The maintainer chose a visible second row over
  markers hidden in names.
- A step adds its value (a *change*) to the running total; an empty value is a gap with no label.
- A total is drawn from zero to the running total. If its value cell is empty it shows the running
  total so far, if it holds a number that number replaces the running total and the chain continues
  from it.
- `ChartState.kind` is `"waterfall"`; `grouping` has no meaning and stays `"stacked"`.
- Layout (`layout/waterfall.py`) follows ADR 0007: the primitive structure depends only on the data.
  Rises, falls and totals use the colour indices 1, 2 and 0.

## Alternatives considered

- **Marker in the category name** (a trailing "="): compact like think-cell, but easy to overlook and
  it pollutes the name.
- **Empty value cell means total**: needs no extra row, but real gaps would no longer be possible.

## Consequences

- Header and series names of the sample data are English; the data sheet is user content.
- A gap draws a zero-height bar. LibreOffice stretches such children when the group is scaled, so the
  resize watcher must run after every resize (it does) or a sliver would appear.
- Connectors, subtotals as running totals and signed step labels are implemented; difference and CAGR
  arrows belong to M4.
