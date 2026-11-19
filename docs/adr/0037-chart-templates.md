# 0037. Chart templates

- Status: accepted
- Date: 2026-11-20

## Context

*Copy chart format* moves a look between charts on one slide. Reusing a whole chart (kind, options,
format, colours, annotations, sample data) across decks needs a file.

## Decision

- **A template is JSON** `{version, name, description, state}`; `state` is exactly
  `state_io.to_json`, so migrations and validation are inherited.
- **The folder** is `<UserConfig>/librecharts/templates` via `PathSettings`, with a home fallback.
- **What is stored**: everything in `ChartState` except the data link and the same-scale group.
  Sample data is kept, so a template opens as a visible chart.
- **Inserting** creates a fresh chart id and state; editing it never touches the file.
- **Deck specifications** may say `"template": "name"`; `data`, `kind`, options and format in the
  entry win. Resolution order is next to the specification, then the template folder, then an
  absolute path.
- No schema bump: the nested state keeps its own version.

## Consequences

Templates can be shared as ordinary JSON files. A newer template is refused with a clear message;
opening it in an older LibreCharts is not supported.
