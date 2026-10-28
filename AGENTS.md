# AGENTS.md

LibreCharts is a think-cell-style chart extension (`.oxt`) for **LibreOffice Impress**, written in
Python-UNO. Charts are drawn as native Draw shapes; chart data is edited in a Calc window.
Status: M0 (scaffold). See [ROADMAP.md](ROADMAP.md) for milestones and non-goals.

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

TODO: no `test-lo` task yet. Integration tests against a real LibreOffice must run under
LibreOffice's own Python (`<LO>/program/python.exe`), not the uv venv. Planned for M1; see
[CONTRIBUTING.md](CONTRIBUTING.md#testing).

## Project map

```
src/librecharts/core/   Pure Python: geometry, scaling, chart models. NO uno imports.
src/librecharts/lo/     UNO adapters: turn core models into shapes, Calc sync. Only place for uno.
extension/              Static .oxt files (manifest, menus, entry.py). entry.py stays thin.
scripts/build_oxt.py    Packs extension/ + src/librecharts + LICENSE into the .oxt
tests/                  Mirrors src/; no LibreOffice required
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
install project-local dependencies that are already declared.

Ask first: `git commit`, `git push`, adding or removing a dependency (`uv add/remove`), changing CI,
the license, or `.claude/settings.json` / `opencode.json`, any global or system installation.

Never: force-push, create tags or releases, read or write `.env*` files, commit secrets,
overwrite files you have not read, skip hooks (`--no-verify`).

The rules above are mirrored as permissions in `.claude/settings.json` and `opencode.json`.

## Pitfalls

- `import uno` in `core/` fails lint (ruff `TID251`). Move the code to `lo/` instead of adding a `noqa`.
- UNO text properties (`shape.String`) only stick after the shape is added to a draw page.
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
4. Changes touching `extension/` or `lo/`: build the `.oxt` and try it in a throwaway profile.

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
