# Plan: Units Mekko and a per-chart option switch

Status: agreed with the maintainer on 2026-10-29.

## Goal

A Marimekko chart can be shown in two variants (think-cell: "100% Mekko" and "Mekko with units"):

- **Percent Mekko** (today, ADR 0009): every column is 100 % high, segments show shares.
- **Units Mekko** (new): column heights are proportional to the column sums, segments show
  absolute values. Widths work as before (width row, else column sum).

The user switches an existing chart between both variants from its context menu or the sidebar.
This is the first chart option that can be changed after inserting; the mechanism should carry
later options (e.g. stacked/clustered, 100 % column charts) without redesign.

Non-goals: annotations on Mekko charts (unchanged, ADR 0010), an options dialog, a value axis.

## Approach

### State (`core/model.py`, `core/state_io.py`)

- New field `ChartState.percent: bool = False`. `True` is only valid for `kind == "mekko"`
  (validated in `__post_init__`); a new Mekko chart starts with `True` (`sample_mekko_state`).
- Schema version 4; migration `_v3_to_v4` sets `percent = (kind == "mekko")`, so every existing
  Mekko stays a percent Mekko. `to_json`/`from_json` read and write `"percent"`.
- Consequence: a document saved with this version cannot be read by older LibreCharts builds
  ("saved by a newer LibreCharts"); the shapes still show (ADR 0002). Acceptable before 1.0.

### Layout (`core/layout/mekko.py`, `core/layout/chart.py`)

- `layout_mekko(data, width, height, percent=True)`; `layout_chart` passes `state.percent`.
- Units variant:
  - Scale: `nice_axis(0, max column sum)`, like stacked columns; no axis drawn.
  - Column height = column sum on that scale; segments stack bottom-up in series order.
  - Segment labels: absolute values (`format_value`), same fit rules as today.
  - Above each column: the column total (style `"total"`).
  - Width value: second label in the category band, below the category name (band grows by
    one label height). The percent variant keeps the width above the column.
  - Series names right of the last column, level with its segments (as today).
- Primitive structure depends on data and variant only, never on size (ADR 0007). Switching the
  variant changes the structure; `chart.redraw` already replaces children, as for annotations.
- `core/mekko.py` (data sheet rules) stays unchanged: negatives count as empty in both variants.

### Command (`lo/commands.py`, `extension/entry.py`)

- New command `org.librecharts:ChangeChart?percent=true|false`, handled like
  `ChangeAnnotation`: parse the query in `core/` (`ValueError` for unknown keys/values), then
  `chart.redraw(doc, group, replace(state, percent=...))`: one undo step.
- On a non-Mekko chart the command shows a message (new key `option_unsupported`).
- The data sheet sync already merges cells/values into the freshly stored state
  (`lo/datasheet.py`), so the option survives edits while the data sheet is open.

### UI (`core/menu.py`, `core/panel.py`, `core/messages.py`)

- Context menu of a Mekko chart: after "Edit chart data", one toggle entry:
  "Show with units" / "Mit Einheiten anzeigen" (percent chart) or
  "Show as 100 %" / "Als 100 % anzeigen" (units chart).
- Sidebar panel: the same toggle as a second button in the "selected chart" section, only
  enabled for Mekko charts. No new icon (empty icon as for "Remove all").
- Status line names the variant: "Marimekko chart (units)" / "Marimekko-Diagramm (Einheiten)".
- Insert stays one entry ("Marimekko chart", percent); no extra toolbar button.

## Affected modules

`core/model.py`, `core/state_io.py`, `core/datasheet.py` (sample), `core/layout/mekko.py`,
`core/layout/chart.py`, `core/menu.py`, `core/panel.py`, `core/messages.py`, new query parser
(in `core/annotations.py` style, likely a small `core/options.py`), `lo/commands.py`,
`extension/entry.py`.

## Tests

- `tests/core`: migration v3 -> v4 for each kind and JSON round trip; validation (`percent` on a
  column chart raises); units layout (heights proportional to sums, absolute labels, totals,
  width labels, structure independent of size, empty/zero columns); percent layout unchanged
  (existing tests stay green); menu and panel toggles per variant; query parsing.
- `tests/lo/test_mekko.py`: dispatch `ChangeChart?percent=false` -> stored state is units and
  shapes change; one `.uno:Undo` restores percent; units state survives ODP and PPTX reload;
  a data sheet edit keeps the variant.

## Docs

New ADR 0012 "Units Mekko and per-chart options" (supersedes the "percent only" decision of
ADR 0009, which gets a pointer); ARCHITECTURE.md (model field, layout/mekko row, options
module); glossary ("Percent Mekko", "Units Mekko", "Chart option"); CHANGELOG; ROADMAP (M3 line);
README if it lists chart variants.

## Decisions (agreed)

1. State: a `percent` field, not a separate chart kind `"mekko_units"` (the toggle would change
   the kind and every kind check would need both).
2. Labels in the units variant: column total above, width below the category name; not the
   width above without totals.
3. Width fallback in the units variant: column sum, the same rule as percent; not equal widths.
4. Insert: toggle only; no separate "Insert units Mekko" entry.
