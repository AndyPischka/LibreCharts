# Architecture

A map of the code and the rules that keep it testable. Decisions and their reasons live in
[docs/adr/](docs/adr/); terms in [docs/glossary.md](docs/glossary.md).

## Layers

```
LibreOffice Impress
   │  menu / dispatch
   ▼
extension/entry.py          UNO protocol handler. Thin: translate a command into a call to lo/.
   │
   ▼
src/librecharts/lo/         UNO adapter. Builds shapes from core models, talks to Calc, reads
   │                        the document. The only package (besides extension/) allowed to import uno.
   ▼
src/librecharts/core/       Pure Python. Chart models, layout, axis scaling. Input: numbers and
                            sizes. Output: plain geometry (rectangles, lines, text positions).
```

Dependencies point downward only: `core` knows nothing about `lo` or `extension`.

## Modules in `core/`

| Module | Role |
|---|---|
| `model.py` | `ChartState`: the persisted description of a chart (raw cells, evaluated values, kind, grouping, schema version) |
| `state_io.py` | `ChartState` <-> JSON with schema migrations; malformed input raises `StateError` |
| `datasheet.py` | Data sheet conventions: cell grid -> `ChartData` (categories, series); sample data |
| `scale.py` | "Nice" value axis ranges |
| `primitives.py` | `Rect`, `Line`, `Text`: layout output in 1/100 mm, styling left to the renderer |
| `layout/column.py` | `ChartData` + size -> primitives for stacked and clustered columns |

Data flow: Calc cells -> `ChartState` (stored in the document) -> `datasheet.parse` -> `ChartData`
-> `layout_column` -> primitives -> `lo/` draws shapes. Stored state is part of the user's files,
so every released schema version must stay readable (`state_io.py`).

## Invariants

1. **`core/` never imports `uno`.** Enforced by ruff (`TID251`) so that the layout logic is unit-testable
   without LibreOffice.
2. **No runtime dependencies.** Everything ships inside the `.oxt` and runs on LibreOffice's bundled
   Python (ADR 0001).
3. **A chart is a group of native Draw shapes** (ADR 0002); the slide still looks right if the
   extension is not installed.
4. **Layout is a pure function** of chart data and available size: same input, same geometry.
5. **The data sheet is a Calc document** (ADR 0003); the chart on the slide is a projection of it.

## Not yet decided

- How chart data and settings are stored inside the slide so a chart can be re-opened for editing
  (idea: serialize into the group shape's user-defined attributes). To be settled in M1 with an ADR.
- The exact Calc ↔ slide synchronisation mechanism (M1 spike).

Update this file whenever a module is added or a boundary changes.
