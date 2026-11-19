# 0038. Data import

- Status: accepted
- Date: 2026-11-20

## Context

Charts start from sample data; users want to bring an existing table into a chart without retyping
it. The Calc data sheet is a view, so an import only needs to replace the stored cells.

## Decision

- **CSV text is parsed in `core/importdata.py`** (delimiter guessed or given); cells become strings,
  values numbers where they parse. A table needs a header and at least one row and column.
- **ODS/XLSX are read through LibreOffice** in `lo/dataimport.py` (hidden, first or named sheet),
  then the same core table replaces the chart's data sheet.
- **Clipboard import** reads text from the system clipboard and inserts a column chart.
- Importing clears a data link: the chart owns its imported data.

## Consequences

CSV is testable without LibreOffice; spreadsheets are integration-tested by hand/`test-lo`.
