# Translating LibreCharts

LibreCharts speaks English and German, plus French, Spanish and Italian. Every further language is
welcome. The decisions behind this page are in [ADR 0031](adr/0031-translations-and-platforms.md).

## Where the strings live

| File | What it is | Who edits it |
|---|---|---|
| `src/librecharts/core/messages.py` | English and German, the source of every string | developers |
| `src/librecharts/core/locales/en.json`, `de.json` | generated copies of the source, for the translation platform | `uv run poe locales` |
| `src/librecharts/core/locales/<language>.json` | one file per further language (two-letter code, e.g. `pt.json`) | translators |

A file holds one flat JSON object: message key -> text. Keys and `{placeholders}` are never
translated. A message missing from a file is shown in English, so a translation can grow step by
step. The menu and toolbar titles are messages too (`addon_*` and `menu_*` keys); the build writes
them into the package.

## With Weblate

Set up one component:

| Setting | Value |
|---|---|
| File format | JSON file |
| File mask | `src/librecharts/core/locales/*.json` |
| Monolingual base language file | `src/librecharts/core/locales/en.json` |
| Template for new translations | `src/librecharts/core/locales/en.json` |
| Language filter | `^(?!en$|de$).*$` (English and German are maintained in code) |
| Source language | English |

Add the repository as push target (pull requests into `main`, Conventional Commits:
`feat(i18n): update <language> translation`). Show `de.json` as a secondary language if German helps
translators.

## By hand

1. Copy `src/librecharts/core/locales/en.json` to `<language>.json` and translate the values.
2. Keep every `{placeholder}`, keep the endings (`.`, `:`, `...`, `?`) and the number of entries of
   comma-separated lists (`gantt_months`: 12, `working_days_names`: 7).
3. `uv run poe check` validates the file; `uv run poe build` packages it.

## Language rules beside the strings

Some formats are code, not text: magnitude suffixes (`core/format.py`, `MAGNITUDE_SUFFIXES`),
decimal commas (`_COMMA_LANGUAGES`) and numeric dates (`core/locale_format.py`, `DAY_FIRST`). A
new language that writes them differently from English needs a line there too, with a test.

## For developers

When you add or change a message in `messages.py`, write it in English and German and run
`uv run poe locales`. The translations of a changed English message are stale until translators
review them; Weblate marks them for you.
