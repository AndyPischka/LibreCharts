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
| `messages.py` | All user-visible strings in English and German (a test enforces both) |
| `datasheet.py` | Data sheet conventions: cell grid -> `ChartData` (categories, series); sample data |
| `scale.py` | "Nice" value axis ranges |
| `primitives.py` | `Rect`, `Line`, `Text`: layout output in 1/100 mm, styling left to the renderer |
| `layout/column.py`, `layout/bar.py` | `ChartData` + size -> primitives for stacked and clustered columns / horizontal bars |
| `layout/common.py` | Value axis and number format shared by both layouts |
| `layout/chart.py` | `layout_chart(state, w, h)`: picks the layout by chart kind |

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
   The kinds and order of primitives depend on the data only, never on the size (ADR 0007).
5. **The chart state in the document is the truth; the Calc data sheet is a view** (ADRs 0003, 0005).
   State lives in a document property anchored by the group name (ADR 0004, schema in ADR 0006).

## Modules in `lo/`

| Module | Role |
|---|---|
| `store.py` | Chart id anchor (group name `librecharts:<id>`), state in a document custom property, `claim` forks renamed copies; no `uno` import, unit-tested with fakes |
| `render.py` | Primitives -> shapes in a group; `rerender` replaces children in place |
| `undo.py` | One explicit undo action per chart operation |
| `chart.py` | `insert_column_chart`, `redraw`: chart operations on a presentation |
| `datasheet.py` | Calc window as a transient view: write stored cells, sync every committed edit back |
| `commands.py` | Menu commands (selection handling, messages); called by `extension/entry.py` |
| `resize.py` | One watcher per presentation: after a resize, re-lays charts out in place (ADR 0007) |
| `ui.py` | UI locale and message boxes; texts come from `core/messages.py` |

Further invariants of the adapter:

6. **A chart group starts with an invisible frame rectangle** covering the full layout box, so the
   group's size equals the layout size and re-rendering at the current size is stable.
7. **Every chart operation is exactly one undo step.** LibreOffice does not record API shape
   inserts, so `lo/undo.py` locks its recording and registers an explicit action.

8. **The data sheet is a view, the document property is the truth.** Every committed Calc edit
   is stored and redrawn immediately; the Calc document's modified flag is reset after each sync,
   so closing it never asks to save. It is never written to disk.

Update this file whenever a module is added or a boundary changes.
