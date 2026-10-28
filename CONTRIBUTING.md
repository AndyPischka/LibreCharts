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
| `lo/store.py` with fake UNO objects | `tests/test_lo_store.py` | no | yes |
| UNO integration (menu, shapes, undo, ODP/PPTX round trip) | `tests/lo/` | yes | no (`uv run poe test-lo`) |

- Do not mock code from this repo. Fake UNO objects only at the `lo/` boundary.
- `core/` has a 90 % coverage gate.
- `test-lo` ([scripts/test_lo.py](scripts/test_lo.py)) builds the `.oxt`, installs it into a throwaway
  profile, starts `soffice --headless` on a private pipe and runs the scripts in `tests/lo/` under
  LibreOffice's own Python (plain scripts with asserts, no pytest there). Set `LIBREOFFICE_PROGRAM`
  if LibreOffice is not found. It is not part of CI yet, because the runners have no LibreOffice 25.8+.
  Verified on Windows only.

## Releases

Not set up yet (M1.0). Tags and releases are created by the maintainer only.
