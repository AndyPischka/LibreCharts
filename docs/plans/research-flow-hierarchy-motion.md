# M31: Research — flow, hierarchy and motion

- Status: open (research, no implementation commitment)
- Milestone: M31 (research)
- Builds on: M2/M3 (waterfall, Mekko), M9 (scatter), M14 (picking), M17 (Gantt), M18 (deck build)
- Decision: one ADR per accepted topic; a rejected topic is recorded in the ADR of the milestone that
  replaced it

## Goal

Some requests do not fit the current layout model: flows between nodes, hierarchies as areas, maps,
repeated small charts and a series-by-series build. Each could be valuable, but each also questions
an invariant (one chart = one group, layout independent of size, no runtime dependencies). This plan
is a set of time-boxed spikes. It produces decisions, prototypes and estimates — not a release
feature list.

## Ground rules

- Every spike ends with a one-page finding: data format, algorithm, primitive types, performance,
  undo/resize behaviour, and a go/no-go recommendation.
- No spike merges drawing code into `core/` without an ADR. Prototypes stay on a branch.
- The invariants of ARCHITECTURE.md stay in force unless the ADR explicitly changes one: native
  shapes, `core/` without UNO, layout as a pure function, state in the document, one undo step.
- No runtime dependency (ADR 0001). Algorithms are written in plain Python; large geodata must ship
  inside the `.oxt` and stay within a reasonable package size.

**Priority (agreed):** Sankey first, then map/choropleth. Treemap, small multiples, series animation
and diagnostics follow. The section order below is the reading order, not the work order.

## Topics

### 1. Sankey

**Question:** can a useful flow diagram be laid out and edited with the existing primitive set?

- Data format: nodes and links or a square matrix (`source, target, value`). A square matrix fits the
  Calc data sheet better and avoids a second sheet; the parser can derive nodes from row/column
  headers.
- Algorithm: layered layout (longest path or a simple iterative ordering), node heights by flow,
  link ribbons as `Polygon`s. Crossing minimisation is the hard part; a deterministic barycentre
  pass with a small iteration count is enough for presentation-sized graphs.
- Labels: node names, values, optional percentages. Hit-testing for annotations is a stretch.
- Failure modes: cycles, zero/negative flows, many nodes, tiny links. Define the fallback (cycle
  breaking, minimum ribbon height, "too complex" message).
- Estimate: medium-high; the layout is the risk, not the rendering.

**Gate:** a 10-node/15-link example that looks acceptable at slide size and resizes without
reordering. If labels cannot be placed legibly, stop.

### 2. Treemap

**Question:** is a squarified treemap better than the existing Mekko for hierarchy?

- Data format: a hierarchy (parent/child/value) needs more than the two-level category/series grid.
  Options: indented rows (`Level 1 | Level 2 | Value`), a path column (`A/B/C`), or a nested JSON
  cell. The indented rows fit the Calc sheet best.
- Algorithm: squarified treemap, deterministic, with a minimum rectangle size; labels only in
  rectangles large enough, with the existing decluttering rules.
- Rendering: `Rect`s with series colours, optional borders; drill-down is not interactive.
- Reuse: the Mekko already teaches variable-width columns and label placement; the treemap adds the
  hierarchy parser.
- Estimate: medium. The algorithm is known; the data model is the design work.

**Gate:** a two-level example with 20 leaves; labels remain readable at slide size. If the data
sheet becomes unintuitive, consider a treemap as a one-off "layout element" generated from a table
instead of a chart kind.

### 3. Map / choropleth

**Question:** can a map be shipped without blowing up the package or violating the licence?

- Geodata: country/region polygons with a permissive licence (e.g. Natural Earth public domain) at a
  size that keeps the `.oxt` reasonable. Simplify aggressively; a slide does not need coastline
  detail. A world map at 1:110m is a few hundred KB as simplified polygons; a country map with
  regions is larger.
- Projection: equirectangular or a simple Mercator; no projection library. Region matching by
  ISO code or name.
- Data format: `Region | Value` rows, optional group/colour column.
- Labels: only for regions above a minimum area; a legend and a colour scale instead of many labels.
- Risk: licence, package size, region naming, and users expecting local administrative maps. This
  may stay a non-goal for the core extension and become an optional data pack.
- Estimate: high; research first.

**Gate:** a world map and one country map with a documented licence and a package size under the
agreed budget. If not, record map charts as a non-goal and point to a picture-based workflow.

### 4. Small multiples

**Question:** can one chart state be repeated over groups without duplicating the chart object?

- Data format: a `group` column (scatter already has one) or a third data-sheet dimension. The
  category/series grid has no group dimension; a fixed-column layout is easier.
- Rendering: one group of shapes containing a grid of mini-plots, each with its own scale or a shared
  scale. The layout must stay a pure function of data and size; the number of panels depends on the
  group count, not on size.
- Labels: a panel title, a shared legend, no per-panel axis unless the grid is small.
- Editing: one data sheet, one chart state, one undo step. Selecting a panel is not needed in v1.
- Alternative: build N separate charts arranged in a grid (M26), each with its own state. Less
  elegant, but it reuses everything and gives per-panel editing.
- Estimate: medium if the separate-charts route is acceptable; high for a true single chart.

**Gate:** decide between "one chart with panels" and "N charts arranged". If the latter, M31 only
adds a command *Repeat chart for each group* and no new layout.

### 5. Series-by-series build (animation)

**Question:** can a chart reveal its series one by one on a slide without breaking the group model?

- LibreOffice animations apply to shapes and groups. A chart is one group; animating children
  individually would require splitting the group or adding separate groups per series.
- Options:
  1. **One group per series** plus a hidden frame group. The chart state would have to be shared by
     several groups or duplicated; resize, undo and the "one chart" identity break.
  2. **LibreOffice's group animation**: animate the whole chart with a fade, not per series. This
     works today and needs no feature.
  3. **Export a sequence of states**: the deck builder creates one slide per build step. This fits
     M18 and avoids the group problem, but duplicates slides.
- Check the UNO animation API on 25.8 and 26.8: can a shape inside a group be an animation target?
  Can an effect be added without the Impress UI? Does it survive ODP/PPTX?
- Estimate: research; likely a no-go for true per-series animation, a go for a build-step slide
  sequence.

**Gate:** a prototype that fades in one series on a real slide and survives save/reload, or a clear
no-go with the reason. If no-go, document "use slide transitions or the deck builder's step slides".

### 6. Diagnostics for large decks

**Question:** where does time go on a deck with many charts, and what can be logged for support?

- Measure: opening a deck, editing data, resizing, updating links, redrawing all charts, design
  check. Use `time.perf_counter` in a test deck, not in production output.
- Identify hot spots: `render.rerender` child reads, `store.all_charts`, link source opening,
  `samescale` redraws. The AGENTS.md notes already warn about reading every child.
- A support report (M29 audit) can include counts and timings without chart data.
- Estimate: small; it informs M22-M30 performance decisions.

**Gate:** a benchmark script and a short report; no user-facing feature unless a bottleneck needs a
fix.

## Approach

1. Work in the agreed order: Sankey, then map/choropleth. Treemap, small multiples, animation and
   diagnostics follow; the issue tracker can reorder within that group.
2. Time-box each spike to a few days. Write the finding in `docs/plans/` first, then an ADR if the
   topic is accepted.
3. Prototype only the risky part: Sankey layout on synthetic data, treemap algorithm, map data size,
   animation API. Do not build UI or persistence until the gate is passed.
4. If a topic is accepted, write a full milestone plan (data sheet, state, layout, UI, tests) before
   implementation, as with every other milestone.
5. If a topic is rejected, record why in the roadmap/non-goals so the question is not reopened
   without new facts.

## Affected modules (if accepted)

| Topic | Likely modules |
|---|---|
| Sankey | `core/sankey.py`, `core/layout/sankey.py`, `model.ChartKind`, `deck.py` |
| Treemap | `core/treemap.py`, `core/layout/treemap.py`, hierarchy parser |
| Map | `core/map.py`, `core/layout/map.py`, bundled geodata, build script |
| Small multiples | `core/layout/*`, a repeat command in `lo/commands.py`, `arrange.py` |
| Animation | `lo/animation.py`, possibly a state/group model change, `lo/deck.py` |
| Diagnostics | `core/benchmark.py` (test only), `lo/audit.py`, CLI `--timings` |

## Test strategy

- Spikes are tested with a small pytest module and a synthetic dataset; no `lo` tests until the gate.
- Layout invariants: same primitive structure for every size, deterministic output for the same
  input, no random order without a seed.
- Performance: a deck with 50 charts and a chart with 500 categories; record timings in the finding.
- Visual: render the prototype to a PNG/ODP by hand and inspect at slide size.

## Open questions

- Sankey and map are the agreed first two. The issue tracker decides the order of the remaining four,
  not this plan.
- Is a map data pack acceptable as a separate download, or must everything ship in the `.oxt`?
- Can a Sankey be useful without interactive node dragging? Static layout only in v1.
- Does a treemap belong in the chart model or in the table/element family?
- Is per-series animation worth a second chart identity, or is a build-step slide sequence enough?
- How much of the diagnostic timing can be exposed without leaking document content?

## Out of scope

- A commitment to ship any of these topics.
- 3D charts, interactive dashboards, live data streaming.
- A general graph layout engine or a GIS projection library.
- Animation authoring beyond the series build question.
