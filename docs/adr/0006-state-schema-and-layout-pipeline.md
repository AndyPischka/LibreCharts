# 0006. Versioned chart state schema and a pure layout pipeline

- Status: accepted
- Date: 2026-10-28

## Context

The chart state is stored inside users' files (ADR 0004) and outlives the code that wrote it. The drawing
logic has to be testable without LibreOffice (ADR 0001).

## Decision

- `ChartState` holds: chart kind, grouping, the raw cell grid (text, numbers, formulas) and the evaluated
  numeric grid, plus a schema version. Both grids are rectangular and equally shaped; values are finite or `None`.
- JSON is compact with the version in `"v"`. `state_io.from_json` validates strictly, migrates old
  versions through a registry (`_MIGRATIONS`, N -> N+1) and refuses newer versions with a clear error.
  Every released schema version must stay readable.
- Pipeline: `ChartState` -> `datasheet.parse` -> `ChartData` -> `layout_column` -> primitives
  (`Rect`, `Line`, `Text`, 1/100 mm, no styling) -> `lo/render` draws shapes, choosing colours and fonts.
- Layout is a pure function of data and size. Re-layout happens on data changes at the group's current size.

## Alternatives considered

- **Store only evaluated values**: loses formulas.
- **Store the drawn geometry**: not editable, and breaks when layout improves.
- **Unversioned JSON**: cannot evolve without breaking existing files.

## Consequences

- Changing the schema requires a version bump and a migration with a test.
- Category and series names come from raw cell text, so a formula in a header cell shows as text.
- Number labels are locale-neutral (`2.5`); localised number formats are not implemented.
- Re-layout when the user resizes the group is not implemented yet.
- Schema 2 added annotations (ADR 0010).
