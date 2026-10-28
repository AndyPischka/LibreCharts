# Contributing

## Setup

```
uv run poe setup
```

This installs Python 3.11 and the dev tools into `.venv` and activates the git hooks.

## Workflow

- Trunk-based: branch from `main`, keep branches short-lived, open a PR into `main`.
- [Conventional Commits](https://www.conventionalcommits.org/): `feat(core): add waterfall layout`.
  Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
  A commit-msg hook checks this.
- `uv run poe check` must pass; CI runs exactly that on Ubuntu and Windows with Python 3.11 and 3.13.
- Which docs a change must touch is listed in [AGENTS.md](AGENTS.md#keep-the-docs-in-sync).

## Testing

| Kind | Where | Needs LibreOffice | Runs in `check` |
|---|---|---|---|
| Unit tests for `core/` (layout, scaling, models) | `tests/core/` | no | yes |
| Packaging tests (`.oxt` contents) | `tests/test_build_oxt.py` | no | yes |
| UNO integration (menu, shape creation, Calc sync) | not yet there | yes | no |

- Do not mock code from this repo. Fake UNO objects only at the `lo/` boundary.
- `core/` has a 90 % coverage gate.
- **TODO (M1):** a `test-lo` task. It must run under LibreOffice's Python, install the `.oxt` into a
  throwaway profile (`-env:UserInstallation=...`), start `soffice --headless` on a socket, and drive it over UNO.
  A manual version of this worked in M0: install, dispatch `org.librecharts:InsertChart`, check the shape count.

## Releases

Not set up yet (M1.0). Tags and releases are created by the maintainer only.
