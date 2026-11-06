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
- `test-lo` ([scripts/test_lo.py](scripts/test_lo.py)) builds the `.oxt` and runs each
  `tests/lo/test_*.py` module in its own `soffice --headless` with a fresh throwaway profile, under
  LibreOffice's own Python (plain `test_*(ctx)` functions, no pytest there). A crash of LibreOffice
  only fails its own module. Set `LIBREOFFICE_PROGRAM` if LibreOffice is not found.
- CI job `integration` runs `test-lo` on Ubuntu against LibreOffice **25.8.7**, the minimum version
  (official packages, extracted, checksum pinned in the workflow). On failure the first error is
  shown as an annotation on the run page. Clipboard tests and tests needing visible documents are
  skipped on headless Linux (they abort LibreOffice there) and run on Windows only.
- Known issue: on headless Linux, LibreOffice often aborts during a test that opens a data sheet
  and closes it again (for example
  `test_annotations::test_editing_data_keeps_an_arrow_added_while_the_data_sheet_is_open`); the
  cause is not found yet. When that happens, the job prints the Python stack of the extension code
  that was running (`PYTHONFAULTHANDLER`) and, from the core dump, a `gdb` backtrace of every
  LibreOffice thread; the crashing thread also appears as an annotation on the run page. Because of
  this, the release workflow runs `check` only; `test-lo` is run locally before a tag.

## Releases

Tags and releases are created by the maintainer only. A `v*` tag starts the release workflow; it
runs `check`, builds the package and creates the GitHub release. It does not run `test-lo` (see the
known issue above), so run it locally before tagging.

1. Set the version in `pyproject.toml`, turn `## [Unreleased]` in
   [CHANGELOG.md](CHANGELOG.md) into `## [<version>] - <date>`, and update
   `extension/description/release-notes_{en,de}.txt`.
2. `uv run poe check` and `uv run poe test-lo` must pass locally.
3. `uv run poe build` writes `dist/LibreCharts-<version>.oxt`; check it by hand if the release is
   important.
4. Commit, tag `v<version>` and push the tag.
5. The release workflow creates the GitHub release with the `.oxt`, its SHA256 and the changelog
   section. Check the run and the release.
6. Upload the same `.oxt` to [extensions.libreoffice.org](https://extensions.libreoffice.org/)
   with the maintainer account. The site takes the version from `description.xml`.
