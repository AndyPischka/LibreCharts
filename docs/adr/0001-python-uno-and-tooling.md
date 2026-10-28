# 0001. Python-UNO extension and project tooling

- Status: accepted
- Date: 2026-10-28

## Context

LibreCharts is a LibreOffice Impress extension, developed solo, open source, targeting Windows,
Linux and macOS. LibreOffice 26.8 on the dev machine bundles Python 3.13 and ships no SDK.

## Decision

- **Language:** Python via PyUNO. Runs on the Python bundled with LibreOffice, needs no compiler or JRE.
- **Minimum:** LibreOffice 25.8 and Python >= 3.11. Documented, not enforced via `description.xml`
  (LibreOffice 26.8 rejected `LibreOffice-minimal-version`; `OpenOffice.org-minimal-version 4.1` is used as baseline).
- **No runtime dependencies**; the pure `core/` is bundled into the `.oxt` as plain source.
- **Tooling:** uv (Python versions, venv, lockfile), poethepoet (tasks in `pyproject.toml`), ruff
  (lint and format), pyright (strict for `core/`), pytest + coverage, pre-commit, GitHub Actions,
  Dependabot.
- **Workflow:** GitHub, trunk-based, Conventional Commits.
- **License:** MPL-2.0, the licence LibreOffice itself uses: changes to LibreCharts files stay open,
  embedding stays unproblematic. (LGPL-2.1 was considered; MPL-2.0 fits an interpreted codebase better.)

## Alternatives considered

- **Java-UNO**: mature bindings, but users need a JRE and builds are heavier.
- **C++-UNO**: best performance, but needs the SDK, per-platform builds, high effort.
- **LibreOffice Basic**: not maintainable at this size.
- **just** instead of poethepoet: nicer syntax, but another global tool and shell differences on Windows.
- **pip + venv**: no global install, but no lockfile and more manual work.

## Consequences

- Extension code cannot use third-party packages; anything needed must be written or vendored.
- Layout logic must stay separate from `uno` to be testable (see [ARCHITECTURE.md](../../ARCHITECTURE.md)).
- Integration tests need LibreOffice's own Python and are not part of `check` yet.
