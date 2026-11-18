# 0028. Automation: deck specification, API and command line

- Status: accepted
- Date: 2026-11-18

## Context

M18 makes a presentation buildable without clicking: a monthly report deck filled from a data file,
and a nightly job that refreshes every data link of a deck. The extension runs inside LibreOffice
(ADR 0001) and ships no runtime dependencies, so every operation must go through UNO, and the
project has no IDL compiler.

## Decision

- **The deck specification is one JSON file** (`core/deck.py`): `version` and a list of `charts`.
  A chart names its `placeholder` and its `kind`, carries its data as a grid (first row category
  names, first column series names, at least 2 x 2 cells) and may set every `ChartState` field a
  user can set: `grouping`, `percent`, `sort`, `doughnut`, `range`, `errors`, `horizontal`,
  `stacked`, `lines`, `secondary`, `colors`, `format`, `calendar`. Unknown keys are errors, so a
  typo cannot pass silently; messages exist in German and English. `format` is merged over the
  defaults a chart inserted from the menu gets, including the locale's separator and language. A
  Gantt chart takes its dates as Calc serial numbers, like its data sheet does.
- **A template marks its places with placeholder shapes** named `librecharts-placeholder:<key>`
  (`core/deck.py` knows the name). The chart is inserted at the placeholder's position and size and
  the placeholder is removed. A chart without a placeholder stops the build *before* anything is
  changed or saved; a placeholder without a chart stays and is named in the report, because one
  template may serve decks that use only some of its sections. Slides, master slides and the colour
  scheme of the template are kept.
- **Building** (`lo/deck.py`) loads the template hidden, with macros never executed and its own links
  left as they are, writes the output through the filter of its extension (`.odp`, `.pptx`) and
  closes the template. It adds no undo actions: nobody looks at the undo list of a template that is
  built and saved in one go, and the explicit actions of `lo/undo.py` hold proxies of that document.
  Hence `chart.insert_at(..., undo_action=False)`.
- **The public API is `librecharts.api`**: `build_deck`, `update_links` (optionally limited to chart
  ids) and `insert_chart` (one undo step). Python scripts inside LibreOffice import it; the command
  line and the macro command use it.
- **The macro API is a dispatch command**, like every other LibreCharts command:
  `org.librecharts:BuildDeck?template=<url>&data=<url>&out=<url>`. "Update all links" already existed.
  A UNO *service* with named methods was tried and dropped: a Python UNO object only exposes
  interface methods to UNO clients, and a service with a single `XJob.execute` could not be called
  through the bridge (`sequence<PropertyValue>` failed to marshal), so it could neither be used
  reliably from Basic nor tested. Dispatch is the mechanism the menu, the sidebar and `tests/lo`
  already use. The report, or the reason nothing was built, appears in a message box; where there
  is no window it is printed (`ui.tell`).
- **The command line** is `uv run poe deck ...`: `build --template ... --data ... --out ...` and
  `update <deck> [--out ...]`. `scripts/deck.py` finds LibreOffice like `scripts/test_lo.py` (shared
  `scripts/loenv.py`), starts a headless soffice with a throwaway profile on a private pipe and runs
  `python -m librecharts.cli` under LibreOffice's Python, which does the work in `lo/worker.py` and
  shuts LibreOffice down. The extension need not be installed: the scheme and locale code falls back
  without its configuration, and the worker imports `librecharts` from `src`.
- **Arguments and help are plain `argparse`** (`core/cli.py`), localized through
  `core/messages.py`, so `uv run poe deck --help` works without LibreOffice. The worker is entered
  with `--pipe`, so the launcher and the worker share one parser.

## Alternatives considered

- **A UNO service with named methods**: see above; the UNO object hides them from every client.
- **A script library registered in `Scripts.xcu`** for Basic: the most natural macro call, but the
  script provider's support for Python libraries inside an extension is undocumented and would need
  its own test that cannot run headless.
- **An IDL interface shipped in the `.oxt`**: the standard solution, but it needs the LibreOffice SDK
  at build time or a checked-in `.rdb`; too much for this milestone.
- **Slide index and position in the specification** instead of placeholders: layout data would move
  into the data file and break as soon as a slide moves.
- **Every placeholder must be used**: a template with optional sections could never be reused.
- **A separate release artifact for the command line**: a repo script covers developers, CI and
  power users; a download is a second release channel to maintain.
- **Undo actions in a built deck**: the build happens in a hidden copy that is saved and closed.

## Consequences

- The deck specification carries its own `version`; `ChartState` does not change, so no migration.
- `chart.insert_at` keeps the caller's format, unlike the menu helpers, which still apply the
  locale's default format; `insertChart` from the Python API is one undo step.
- A build never runs macros of the template and never touches its own data links.
- Macro authors see the report in a message box; headless callers read it from the console.
- The command line needs an installed LibreOffice but no additional Python packages.
- The launcher, the worker and the dispatch command share `librecharts.api`, so a new automation
  feature has one implementation, not three.
