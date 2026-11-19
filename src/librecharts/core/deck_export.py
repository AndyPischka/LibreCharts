"""Export charts of a presentation as a deck specification (M29)."""

from __future__ import annotations

import json

from librecharts.core.model import ChartState

VERSION = 1


def state_to_entry(placeholder: str, state: ChartState) -> dict[str, object]:
    """One chart entry of a deck specification from a stored chart state."""
    entry: dict[str, object] = {
        "placeholder": placeholder,
        "kind": state.kind,
        "grouping": state.grouping,
        "data": [[_cell(cell) for cell in row] for row in state.cells],
        "format": {
            "axis": state.format.axis,
            "gridlines": state.format.gridlines,
            "series_names": state.format.series_names,
            "decimals": state.format.decimals,
            "magnitude": state.format.magnitude,
            "unit": state.format.unit,
            "separator": state.format.separator,
            "language": state.format.language,
            "markers": state.format.markers,
            "patterns": state.format.patterns,
        },
    }
    for flag in ("percent", "doughnut", "range", "errors", "horizontal", "stacked", "pareto"):
        if getattr(state, flag):
            entry[flag] = True
    if state.sort != "none":
        entry["sort"] = state.sort
    if state.lines:
        entry["lines"] = list(state.lines)
    if state.secondary:
        entry["secondary"] = list(state.secondary)
    if state.colors:
        entry["colors"] = list(state.colors)
    return entry


def to_json(entries: list[tuple[str, ChartState]]) -> str:
    """The specification of a whole presentation."""
    return json.dumps(
        {"version": VERSION, "charts": [state_to_entry(name, state) for name, state in entries]},
        indent=2,
        ensure_ascii=False,
    )


def _cell(cell: str) -> object:
    text = cell.strip()
    if not text:
        return None
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return cell
    return int(number) if number.is_integer() else number
