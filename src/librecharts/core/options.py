"""Chart options: switches the user can change after inserting a chart (ADR 0012).

Today only a Marimekko chart has one: percent (every column 100 % high) or units (column heights
follow the column sums). The command ``ChangeChart?percent=true|false`` sets it.
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qs

from librecharts.core.model import ChartState


def toggle(state: ChartState) -> tuple[str, str] | None:
    """The switch offered for ``state``: (message key of its title, command), or ``None``.

    The switch always leads to the other value of the option.
    """
    if state.kind != "mekko":
        return None
    if state.percent:
        return "menu_mekko_units", "ChangeChart?percent=false"
    return "menu_mekko_percent", "ChangeChart?percent=true"


def changed(state: ChartState, query: str) -> ChartState:
    """``state`` with the option in ``query`` (``percent=false``) applied.

    Raises ``ValueError`` for missing, unknown or invalid arguments and for options the chart
    kind does not have.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    if set(args) != {"percent"}:
        raise ValueError(f"unknown chart option: {sorted(args)}")
    value = {"true": True, "false": False}.get(args["percent"])
    if value is None:
        raise ValueError(f"percent must be true or false, not {args['percent']!r}")
    if state.kind != "mekko":
        raise ValueError(f"a {state.kind} chart has no percent option")
    return replace(state, percent=value)
