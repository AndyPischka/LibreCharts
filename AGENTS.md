# AGENTS.md

LibreCharts is a think-cell-style chart extension (`.oxt`) for **LibreOffice Impress**, written in
Python-UNO. Charts are drawn as native Draw shapes; chart data is edited in a Calc window.
Status: M1-M3 done (column/bar, waterfall, Marimekko). See [ROADMAP.md](ROADMAP.md) for milestones and non-goals.

## Commands

Run everything through `uv run poe <task>` (uv installs Python 3.11 and the dev tools on demand).

| Task | What it does |
|---|---|
| `uv run poe setup` | `uv sync` + install git hooks (pre-commit and commit-msg) |
| `uv run poe check` | lint + format-check + typecheck + test; **exactly what CI runs** |
| `uv run poe test` | pytest with coverage gate (90 % on `librecharts.core`) |
| `uv run poe lint` / `format` | ruff check / ruff format (in place) |
| `uv run poe typecheck` | pyright (strict for `core/`, basic elsewhere) |
| `uv run poe build` | build `dist/LibreCharts-<version>.oxt` |
| `uv run poe test-lo` | UNO integration tests against a real LibreOffice (not in `check`; CI job `integration`) |

`test-lo` needs LibreOffice installed (override discovery with `LIBREOFFICE_PROGRAM`). It uses a
throwaway profile and LibreOffice's own Python, one LibreOffice per `tests/lo` module, see
[CONTRIBUTING.md](CONTRIBUTING.md#testing). Runs on Windows and in CI on Linux against the minimum
version 25.8.7; macOS is untested.

## Project map

```
src/librecharts/core/   Pure Python: geometry, scaling, chart models. NO uno imports.
src/librecharts/lo/     UNO adapters: turn core models into shapes, Calc sync. Only place for uno.
extension/              Static .oxt files (manifest, menus, entry.py). entry.py stays thin.
scripts/build_oxt.py    Packs extension/ + src/librecharts + LICENSE into the .oxt
tests/                  Mirrors src/; no LibreOffice required
tests/lo/               UNO integration tests (`test_*(ctx)`), run under LibreOffice's Python
docs/adr/               Architecture decision records     docs/plans/   Plans for large features
```

Architecture, layering and invariants: [ARCHITECTURE.md](ARCHITECTURE.md).
Domain terms: [docs/glossary.md](docs/glossary.md). Use them consistently in code and docs.

## Conventions

- Code, comments, docs: **English**. UI strings: German + English (both required for every string).
- Python >= 3.11 (the minimum is set by the supported LibreOffice versions). No runtime
  dependencies: the extension runs inside LibreOffice's bundled Python (ADR 0001).
- Commits: Conventional Commits (`feat(core): ...`), enforced by a commit-msg hook. Trunk-based:
  short-lived branches, PRs into `main`.
- `core/` stays testable without LibreOffice. If you need `uno`, the code belongs in `lo/`.
- Tests assert behaviour of public functions; do not mock what you own. UNO objects may be faked
  at the `lo/` boundary only.

## Boundaries

Allowed without asking: edit code, tests and docs; run `uv run poe ...`, `uv sync`, `git status/diff/log`;
install project-local dependencies that are already declared; `git commit` and `git push` to `main`
once `check` is green (Conventional Commits, logically split commits).

Ask first: adding or removing a dependency (`uv add/remove`), changing CI,
the license, or `.claude/settings.json` / `opencode.json`, any global or system installation.

Never: force-push, create tags or releases, read or write `.env*` files, commit secrets,
overwrite files you have not read, skip hooks (`--no-verify`).

The rules above are mirrored as permissions in `.claude/settings.json` and `opencode.json`.

## Pitfalls

- `import uno` in `core/` fails lint (ruff `TID251`). Move the code to `lo/` instead of adding a `noqa`.
- UNO text properties (`shape.String`) only stick after the shape is added to a draw page or group.
- LibreOffice does not record shapes inserted via the API for undo. Wrap chart changes in
  `lo/undo.py` (lock recording, add one explicit action); an undo context alone is a no-op entry.
- Extensions cannot add tabs to the Notebookbar (ribbon): its tabs are fixed in LibreOffice. An
  `OfficeToolBar` in `Addons.xcu` is shown in its "Extension" group and in the classic UI.
- Pass `None` for a void `any` argument. `uno.Any(...)` as a plain call argument works on
  LibreOffice 26.8 but raises on 25.8 ("use uno.invoke instead"); CI tests on 25.8.
- Never let an exception escape a dispatch or a UNO listener: LibreOffice may abort. `entry.py`
  and the listeners in `lo/` catch and print them.
- On documents, `addEventListener` is ambiguous in PyUNO and picks the wrong interface. Use
  `addDocumentEventListener` for document lifetime events.
- In headless mode LibreOffice 26.8 intermittently aborts when a *visible* Calc window is closed.
  Keep test documents hidden; data sheets of hidden presentations open hidden too.
- In `tests/lo`, trigger undo/redo with `helpers.uno_command(ctx, doc, ".uno:Undo")`, never
  `XUndoManager.undo()` (aborted LibreOffice; enforced by `tests/test_lo_conventions.py`).
- Document-open jobs run for visible documents only; reload with `hidden=False` to test them.
- Layout output must have the same primitive structure for every size (resize re-layout, ADR 0007).
- In `tests/lo`, read a shape's geometry in one pass (`child = group.getByIndex(i)`, read, move
  on). Proxies collected in a list and read later intermittently returned default geometry
  (0, 0, 100, 100) in LibreOffice 26.8.
- Code that must run *inside LibreOffice* (resize watcher, document job) only runs there: importing
  `librecharts.lo.resize` in a test starts a watcher in the test process, not in LibreOffice. Insert
  charts through `dispatch(ctx, doc, "org.librecharts:...")` when a test needs the watcher.
- LibreOffice scales group children when the group is resized; zero-size children (waterfall gaps)
  become non-zero. The resize watcher puts them back, so never skip it for such charts.
- Simulated clicks (`helpers.click`, Toolkit robot) need a visible document. LibreOffice counts
  double-clicks itself from press timing; it ignores a `ClickCount` you send, so send two quick
  presses. `test-lo` gives each module a fresh profile: with a shared one, clicks of a later
  module missed their target.
- Clipboard tests and tests needing visible documents call `helpers.skip_on_headless_linux(...)`:
  both abort LibreOffice in headless Linux (CI). They run locally on Windows.
- `tests/lo/` holds plain `test_*(ctx)` functions run by `tests/lo/runner.py`, not pytest; pytest
  ignores that directory. Shared helpers live in `tests/lo/helpers.py`.
- Do not use `LibreOffice-minimal-version` in `extension/description.xml`: LibreOffice 26.8 rejected
  it ("unsatisfied dependencies"). The minimum, LibreOffice 25.8, is documented, not enforced.
- Never kill `soffice` processes by name; the user may have documents open. Use a throwaway
  profile (`-env:UserInstallation=file:///.../tmp_profile`) for experiments and let the script
  call `desktop.terminate()` itself.
- Windows is the primary dev OS; use forward slashes in scripts and avoid shell-specific syntax in poe tasks.

## Definition of done

1. `uv run poe check` passes locally.
2. New behaviour has tests; `core/` coverage stays >= 90 %.
3. Docs updated per the table below.
4. Changes touching `extension/` or `lo/`: `uv run poe test-lo` passes (add a test in `tests/lo/`).

## Keep the docs in sync

| Change | Update |
|---|---|
| New dependency, tool or architecture decision | new ADR in `docs/adr/` |
| New module or changed module boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| New or changed command | this file + [README.md](README.md) |
| New domain term | [docs/glossary.md](docs/glossary.md) |
| Milestone reached or moved | [ROADMAP.md](ROADMAP.md) |
| User-visible change | [CHANGELOG.md](CHANGELOG.md) |

## Larger features

Before implementing anything that spans several modules, write a plan to `docs/plans/<topic>.md`
and get it agreed. After implementation, delete the plan; move lasting decisions into an ADR first.
See [docs/plans/README.md](docs/plans/README.md).

## This file is living

If an agent makes the same mistake twice, add the rule here, or better, enforce it in the linter.
