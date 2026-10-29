"""Chart options: switches the user can change after inserting a chart (ADRs 0012, 0013).

Column and bar charts switch between stacked, clustered and 100 %, and sort their categories by
value. Area charts switch between stacked and 100 %. A Marimekko chart switches between percent and
units. On a column chart, single series can be drawn as lines, optionally on a secondary axis.

Every switch is one ``ChangeChart`` command with a single argument, so each click is one undo step.
The two line switches ``line=<index>`` and ``secondary=<index>`` carry ``on=true`` or ``on=false``
along with the series index.
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
    if state.kind == "area":
        return (
            Switch("menu_stacked", "ChangeChart?grouping=stacked", not state.percent),
            Switch("menu_percent", "ChangeChart?percent=true", state.percent),
        )
    if state.kind not in ("column", "bar"):
        return ()
    clustered = state.grouping == "clustered"
    return (
        Switch("menu_stacked", "ChangeChart?grouping=stacked", not clustered and not state.percent),
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


def can_draw_lines(state: ChartState) -> bool:
    """Whether the chart can show series as lines: a column chart that is not 100 %."""
    return state.kind == "column" and not state.percent


def line_query(index: int, on: bool) -> str:
    """The command that draws series ``index`` as a line (or as a column again)."""
    return f"ChangeChart?line={index}&on={'true' if on else 'false'}"


def secondary_query(index: int, on: bool) -> str:
    """The command that moves line series ``index`` to the right-hand axis (or back)."""
    return f"ChangeChart?secondary={index}&on={'true' if on else 'false'}"


def changed(state: ChartState, query: str) -> ChartState:
    """``state`` with the option in ``query`` (``grouping=clustered``) applied.

    One option per call; the line switches also take ``on=true`` or ``on=false``. Raises
    ``ValueError`` for missing, unknown or invalid arguments and for options the chart kind does
    not have.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    if len(args) == 1:
        key, value = next(iter(args.items()))
    elif set(args) == {"line", "on"}:
        key, value = "line", args["line"]
    elif set(args) == {"secondary", "on"}:
        key, value = "secondary", args["secondary"]
    else:
        raise ValueError(f"expected exactly one chart option, got {sorted(args)}")
    if key == "grouping":
        return _grouping(state, value)
    if key == "percent":
        return _percent(state, value)
    if key == "sort":
        return _sort(state, value)
    if key in ("line", "secondary"):
        return _line(state, key, value, args.get("on", "true"))
    raise ValueError(f"unknown chart option: {key!r}")


def _grouping(state: ChartState, value: str) -> ChartState:
    if state.kind not in ("column", "bar", "area"):
        raise ValueError(f"a {state.kind} chart has no grouping option")
    if value not in ("stacked", "clustered"):
        raise ValueError(f"grouping must be stacked or clustered, not {value!r}")
    if state.kind == "area" and value == "clustered":
        raise ValueError("an area chart is always stacked")
    grouping: Grouping = "clustered" if value == "clustered" else "stacked"
    # Choosing a layout leaves the 100 % variant.
    return replace(state, grouping=grouping, percent=False)


def _percent(state: ChartState, value: str) -> ChartState:
    enabled = {"true": True, "false": False}.get(value)
    if enabled is None:
        raise ValueError(f"percent must be true or false, not {value!r}")
    if state.kind == "mekko":
        return replace(state, percent=enabled)
    if state.kind not in ("column", "bar", "area"):
        raise ValueError(f"a {state.kind} chart has no percent option")
    if not enabled:
        return replace(state, percent=False)
    # 100 % works from every variant: a clustered chart becomes stacked first. Line series have no
    # meaning in a 100 % chart, so they fall back to columns.
    return replace(state, grouping="stacked", percent=True, lines=(), secondary=())


def _sort(state: ChartState, value: str) -> ChartState:
    if state.kind not in ("column", "bar"):
        raise ValueError(f"a {state.kind} chart cannot be sorted")
    if value not in ("none", "descending", "ascending"):
        raise ValueError(f"sort must be none, descending or ascending, not {value!r}")
    sort: SortOrder = (
        "descending" if value == "descending" else ("ascending" if value == "ascending" else "none")
    )
    return replace(state, sort=sort)


def _line(state: ChartState, key: str, index_text: str, on_text: str) -> ChartState:
    """Draw one series as a line (``line``) or move it to the secondary axis (``secondary``)."""
    if state.kind != "column":
        raise ValueError(f"a {state.kind} chart cannot draw series as lines")
    if state.percent:
        raise ValueError("a 100 % chart cannot draw series as lines")
    on = {"true": True, "false": False}.get(on_text)
    if on is None:
        raise ValueError(f"on must be true or false, not {on_text!r}")
    try:
        index = int(index_text)
    except ValueError:
        raise ValueError(f"series index must be a number, not {index_text!r}") from None
    if not 0 <= index < len(state.values) - 1:
        raise ValueError(f"no series with index {index}")
    lines = set(state.lines)
    secondary = set(state.secondary)
    if key == "line":
        if on:
            lines.add(index)
        else:  # a series that stops being a line leaves the secondary axis too
            lines.discard(index)
            secondary.discard(index)
    elif on:  # the secondary axis always carries a line
        lines.add(index)
        secondary.add(index)
    else:
        secondary.discard(index)
    return replace(state, lines=tuple(sorted(lines)), secondary=tuple(sorted(secondary)))
