"""Chart options: switches the user can change after inserting a chart (ADRs 0012, 0013).

Column and bar charts switch between stacked, clustered and 100 %, and sort their categories by
value. A Marimekko chart switches between percent and units. Every switch is one
``ChangeChart`` command with a single argument, so each click is one undo step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from urllib.parse import parse_qs

from librecharts.core.model import ChartState, Grouping, SortOrder


@dataclass(frozen=True, slots=True)
class Switch:
    """One choice in the UI: its title key, its command, and whether it is the current value."""

    title: str
    command: str
    current: bool = False


def variants(state: ChartState) -> tuple[Switch, ...]:
    """The layout variants of a chart, the current one included (for marking it)."""
    if state.kind == "mekko":
        return (
            Switch("menu_mekko_percent", "ChangeChart?percent=true", state.percent),
            Switch("menu_mekko_units", "ChangeChart?percent=false", not state.percent),
        )
    if state.kind not in ("column", "bar"):
        return ()
    clustered = state.grouping == "clustered"
    return (
        Switch(
            "menu_stacked",
            "ChangeChart?grouping=stacked&percent=false",
            not clustered and not state.percent,
        ),
        Switch("menu_clustered", "ChangeChart?grouping=clustered", clustered),
        Switch("menu_percent", "ChangeChart?percent=true", state.percent),
    )


def sort_options(state: ChartState) -> tuple[Switch, ...]:
    """The sort orders of a column or bar chart, the current one included."""
    if state.kind not in ("column", "bar"):
        return ()
    return (
        Switch("menu_sort_none", "ChangeChart?sort=none", state.sort == "none"),
        Switch(
            "menu_sort_descending",
            "ChangeChart?sort=descending",
            state.sort == "descending",
        ),
        Switch("menu_sort_ascending", "ChangeChart?sort=ascending", state.sort == "ascending"),
    )


def sort_toggle(state: ChartState) -> Switch | None:
    """The next sort order in the cycle none -> descending -> ascending -> none."""
    if state.kind not in ("column", "bar"):
        return None
    following: dict[SortOrder, SortOrder] = {
        "none": "descending",
        "descending": "ascending",
        "ascending": "none",
    }
    order = following[state.sort]
    return Switch(f"menu_sort_{order}", f"ChangeChart?sort={order}")


def changed(state: ChartState, query: str) -> ChartState:
    """``state`` with the option in ``query`` (``grouping=clustered``) applied.

    One key per call. Raises ``ValueError`` for missing, unknown or invalid arguments and for
    options the chart kind does not have.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    if len(args) != 1:
        raise ValueError(f"expected exactly one chart option, got {sorted(args)}")
    key, value = next(iter(args.items()))
    if key == "grouping":
        return _grouping(state, value)
    if key == "percent":
        return _percent(state, value)
    if key == "sort":
        return _sort(state, value)
    raise ValueError(f"unknown chart option: {key!r}")


def _grouping(state: ChartState, value: str) -> ChartState:
    if state.kind not in ("column", "bar"):
        raise ValueError(f"a {state.kind} chart has no grouping option")
    if value not in ("stacked", "clustered"):
        raise ValueError(f"grouping must be stacked or clustered, not {value!r}")
    grouping: Grouping = "clustered" if value == "clustered" else "stacked"
    # Clustered charts cannot be 100 % charts; switching to clustered leaves the 100 % variant.
    return replace(
        state, grouping=grouping, percent=False if grouping == "clustered" else state.percent
    )


def _percent(state: ChartState, value: str) -> ChartState:
    enabled = {"true": True, "false": False}.get(value)
    if enabled is None:
        raise ValueError(f"percent must be true or false, not {value!r}")
    if state.kind == "mekko":
        return replace(state, percent=enabled)
    if state.kind not in ("column", "bar"):
        raise ValueError(f"a {state.kind} chart has no percent option")
    if not enabled:
        return replace(state, percent=False)
    # 100 % works from every variant: a clustered chart becomes stacked first.
    return replace(state, grouping="stacked", percent=True)


def _sort(state: ChartState, value: str) -> ChartState:
    if state.kind not in ("column", "bar"):
        raise ValueError(f"a {state.kind} chart cannot be sorted")
    if value not in ("none", "descending", "ascending"):
        raise ValueError(f"sort must be none, descending or ascending, not {value!r}")
    sort: SortOrder = (
        "descending" if value == "descending" else ("ascending" if value == "ascending" else "none")
    )
    return replace(state, sort=sort)
