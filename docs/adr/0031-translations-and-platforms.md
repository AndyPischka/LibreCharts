# 0031. Translations and platforms

- Status: accepted
- Date: 2026-11-19

## Context

Every UI string existed in English and German, kept side by side in `core/messages.py` (AGENTS.md).
That serves the two languages of the maintainers, but not the users of the many other LibreOffice
UI languages. M21 asks for further UI languages through a translation platform (Weblate) and for
macOS to be tested and supported. The menu and toolbar titles are a second copy of strings, in
`extension/Addons.xcu`, which no translation platform can edit.

## Decision

- **English and German stay in `MESSAGES`.** They are the source of every translation: a new string
  is written in both by whoever adds it, and tests keep placeholders and punctuation in step.
- **Further languages are flat JSON files** `src/librecharts/core/locales/<language>.json`
  (message key -> text). Weblate edits this format as "JSON file" with `en.json` as the monolingual
  base and `de.json` as an extra reference. Both are generated from `MESSAGES` by
  `uv run poe locales`; a test fails while they are out of date.
- **`messages.text` looks up** `MESSAGES` for English and German, the JSON file for other
  languages, and falls back to English for anything missing. A file that cannot be read, or holds
  anything but strings of known keys, counts as missing: a broken translation can never break the
  extension. Files are read once per process.
- **Shipped languages**: French, Spanish and Italian, the largest LibreOffice user communities
  after English and German in Europe and Latin America, complete at release. Tests require every
  shipped file to be complete and every file to keep the English placeholders, endings and list
  lengths (month and weekday names).
- **Menu and toolbar titles** get a message key each (`ADDON_KEYS`; `addon_*` keys where no
  existing message fits). `Addons.xcu` keeps English and German, tests compare them with the
  messages, and `scripts/build_oxt.py` writes every further language into the packaged
  `Addons.xcu`. The package also carries the JSON files.
- **Locale rules beside the strings**: magnitude suffixes (`fr`: k, M, Md; `es`: mil, M, mil M;
  `it`: k, Mln, Mrd) and numeric dates (`core/locale_format.py`: `30.06.2026` in German,
  `30/06/2026` in French, Spanish and Italian, ISO otherwise). The date fields already read day-first
  dates in every language but English.
- **macOS**: `scripts/loenv.py` finds LibreOffice in `/Applications` and `~/Applications` and its
  Python in `Contents/Resources`. CI is to run `poe check` on macOS and the integration tests
  against the same minimum LibreOffice as on Linux (the official disk image, checksum pinned);
  that workflow change waits for the maintainer (AGENTS.md: CI changes are agreed first).

## Alternatives considered

- **gettext (`.po`/`.mo`)**: the standard of LibreOffice itself and well supported by Weblate, but
  `.mo` files need a build step and `gettext` lookups by English text break whenever the English
  wording is polished; keys are already what the code uses.
- **Moving English and German into JSON too**: one format for all languages, but the source would
  lose its review in code (tests on placeholders, the diff in a pull request next to the code that
  uses it). Generated `en.json`/`de.json` give the platform the same data.
- **Translating `Addons.xcu` by hand**: a third copy of every title that translators cannot reach;
  generating it from the messages keeps one place per string.
- **Translating more languages up front by machine**: unreviewed text in a professional tool reads
  worse than English. Further languages come through the platform, reviewed by native speakers.

## Consequences

- AGENTS.md's rule changes: every string still needs English and German; other languages are
  optional and fall back to English. After changing a message, run `uv run poe locales`.
- A changed English message leaves its translations stale until translators update them; Weblate
  marks them as needing review because the source changed.
- The release notes and the extension description exist in the shipped languages; release notes
  of further versions are written in English and German and translated through the platform.
- macOS is supported by the scripts; it counts as tested once the CI job runs. Headless-only
  limits (dialogs, clipboard) apply as on Linux.
