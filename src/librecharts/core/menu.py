"""The LibreCharts entries in the context menu of a selected chart (M4 plan, "Interaction").

Built as plain data, so its contents are tested without LibreOffice; ``lo/contextmenu.py`` turns
it into menu entries. Every entry dispatches an ``org.librecharts:`` command.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core import elements, options, style
from librecharts.core import format as formats
from librecharts.core.axis_break import describe
from librecharts.core.datasheet import ChartData
from librecharts.core.elements import Element
from librecharts.core.gantt import parse_gantt, to_date
from librecharts.core.layout.common import format_value
from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState, Format
from librecharts.core.picking import supports
from librecharts.core.scatter import parse_scatter
from librecharts.core.timescale import format_date

PROTOCOL = "org.librecharts:"


@dataclass(frozen=True, slots=True)
class MenuItem:
    """An entry: a command, a submenu (``children``), or a separator (no title)."""

    title: str = ""
    command: str = ""
    children: tuple[MenuItem, ...] = ()


SEPARATOR = MenuItem()


def chart_menu(
    state: ChartState, locale: str, palette: tuple[int, ...] = style.PALETTE
) -> MenuItem:
    """The "LibreCharts" submenu for a chart with ``state`` and the document's scheme palette."""
    data = notes.measured(state)
    items = [_command("menu_show_data" if state.link else "menu_edit_data", "EditData", locale)]
    items += _link_items(state, locale)
    items += [
        _command(switch.title, switch.command, locale)
        for switch in options.variants(state)
        if not switch.current
    ]
    line_menu = _line_menu(state, data, locale)
    if line_menu.children:
        items.append(line_menu)
    colour_menu = _colour_menu(state, data, palette, locale)
    if colour_menu.children:
        items.append(colour_menu)
    sorts = tuple(
        _command(switch.title, switch.command, locale)
        for switch in options.sort_options(state)
        if not switch.current
    )
    if sorts:
        items.append(MenuItem(text("menu_sort", locale), children=sorts))
    formats_menu = _format_menu(state, locale)
    if formats_menu.children:
        items.append(formats_menu)
    items += [
        SEPARATOR,
        _command("menu_copy_format", "CopyChartFormat", locale),
        _command("menu_apply_format", "ApplyChartFormat", locale),
    ]
    if state.scale_group is not None:
        items.append(_command("menu_remove_same_scale", "RemoveSameScale", locale))
    if supports(state, "difference"):
        items += [
            SEPARATOR,
            _command("menu_add_difference", "PickAnnotation?kind=difference", locale),
            _command("menu_add_level", "PickAnnotation?kind=difference&style=level", locale),
            _command("menu_add_cagr", "PickAnnotation?kind=cagr", locale),
        ]
    if supports(state, "axis_break") or supports(state, "value_line"):
        if not supports(state, "difference"):
            items.append(SEPARATOR)
        if supports(state, "axis_break"):
            items.append(_command("menu_add_break", "AxisBreak", locale))
        if supports(state, "value_line") and state.kind == "gantt":
            items.append(_command("menu_add_date_line", "ValueLine", locale))
            items.append(_command("menu_add_today_line", "TodayLine", locale))
        elif supports(state, "value_line"):
            items.append(_command("menu_add_value_line", "ValueLine", locale))
    shown = [
        (index, annotation)
        for index, annotation in enumerate(state.annotations)
        if notes.drawable(annotation, data, state.kind)
    ]
    dates = state.kind == "gantt"
    if shown:
        items.append(SEPARATOR)
        items += [
            MenuItem(
                annotation_title(annotation, data, locale, state.format, dates=dates),
                children=_actions(index, annotation, locale, dates=dates),
            )
            for index, annotation in shown
        ]
        items.append(_command("menu_remove_all", "RemoveAnnotations", locale))
    return MenuItem("LibreCharts", children=tuple(items))


GRID_COLUMNS = (2, 3, 4)  # the "Grid" entries of the Arrange commands


def element_menu(element: Element, locale: str) -> MenuItem:
    """The "LibreCharts" submenu for a selected Harvey ball or check mark: the other states."""
    if element.kind == "harvey":
        states = [
            MenuItem(
                text("menu_harvey", locale, level=str(level)),
                f"{PROTOCOL}SetElement?harvey={level}",
            )
            for level in elements.HARVEY_LEVELS
            if str(level) != element.value
        ]
    else:
        states = [
            MenuItem(text(f"menu_check_{symbol}", locale), f"{PROTOCOL}SetElement?check={symbol}")
            for symbol in elements.CHECK_SYMBOLS
            if symbol != element.value
        ]
    return MenuItem(
        "LibreCharts",
        children=(_command("menu_element_next", "SetElement?next=1", locale), *states),
    )


def arrange_items(locale: str) -> tuple[MenuItem, ...]:
    """The commands that arrange the selected shapes (same size, grid, swap)."""
    return (
        _command("menu_arrange_width", "Arrange?op=width", locale),
        _command("menu_arrange_height", "Arrange?op=height", locale),
        _command("menu_arrange_size", "Arrange?op=size", locale),
        *(
            MenuItem(
                text("menu_arrange_grid", locale, columns=str(columns)),
                f"{PROTOCOL}Arrange?op=grid&columns={columns}",
            )
            for columns in GRID_COLUMNS
        ),
        _command("menu_arrange_swap", "Arrange?op=swap", locale),
    )


def _command(key: str, command: str, locale: str) -> MenuItem:
    return MenuItem(text(key, locale), PROTOCOL + command)


def _link_items(state: ChartState, locale: str) -> list[MenuItem]:
    """ "Link data..." for a chart with its own data; "Update link" and a "Data link" submenu for
    a linked one (ADR 0020)."""
    if state.link is None:
        return [_command("menu_link_data", "LinkData", locale)]
    return [
        _command("menu_update_link", "UpdateLink", locale),
        MenuItem(
            text("menu_data_link", locale),
            children=(
                _command("menu_change_link", "LinkData", locale),
                _command("menu_open_source", "OpenSource", locale),
                _command("menu_remove_link", "RemoveLink", locale),
            ),
        ),
    ]


def _line_menu(state: ChartState, data: ChartData, locale: str) -> MenuItem:
    """The "Series as lines" submenu of a column chart: per series, line/column and axis."""
    entries: list[MenuItem] = []
    if options.can_draw_lines(state):
        for index, series in enumerate(data.series):
            is_line = index in state.lines
            entries.append(
                MenuItem(
                    text(
                        "menu_series_as_column" if is_line else "menu_series_as_line",
                        locale,
                        name=series.name,
                    ),
                    PROTOCOL + options.line_query(index, not is_line),
                )
            )
            if is_line:
                on_secondary = index in state.secondary
                entries.append(
                    MenuItem(
                        text(
                            "menu_primary_axis" if on_secondary else "menu_secondary_axis",
                            locale,
                            name=series.name,
                        ),
                        PROTOCOL + options.secondary_query(index, not on_secondary),
                    )
                )
    return MenuItem(text("menu_line_series", locale), children=tuple(entries))


def _colour_menu(
    state: ChartState, data: ChartData, palette: tuple[int, ...], locale: str
) -> MenuItem:
    """The "Series colour" submenu: per series, its default colour and every palette entry."""
    if state.kind == "waterfall":  # its colours mean increase, decrease and total, not series
        return MenuItem(text("menu_series_color", locale))
    series_items: list[MenuItem] = []
    for index, name in enumerate(_series_names(state, data, locale)):
        current = state.colors[index] if index < len(state.colors) else None
        entries: list[MenuItem] = []
        if current is not None:
            entries.append(
                MenuItem(
                    text("menu_color_default", locale),
                    PROTOCOL + options.color_query(index, None),
                )
            )
        entries += [
            MenuItem(
                text("menu_color", locale, index=str(entry + 1)),
                PROTOCOL + options.color_query(index, entry),
            )
            for entry in range(len(palette))
            if entry != current
        ]
        if entries:
            series_items.append(MenuItem(name, children=tuple(entries)))
    return MenuItem(text("menu_series_color", locale), children=tuple(series_items))


def _series_names(state: ChartState, data: ChartData, locale: str) -> list[str]:
    """What gets its own colour: the series, on a scatter chart the groups, on a Gantt chart the
    phases (all bars, if there is no phase)."""
    if state.kind == "scatter":
        return [name or f"{index + 1}" for index, name in enumerate(parse_scatter(state).groups)]
    if state.kind == "gantt":
        phases = parse_gantt(state).phases
        return [name or f"{index + 1}" for index, name in enumerate(phases)] or [
            text("menu_gantt_bars", locale)
        ]
    return [series.name for series in data.series]


def _format_menu(state: ChartState, locale: str) -> MenuItem:
    """The "Format" submenu: axis/gridline toggles, series names, number format."""
    switches = formats.format_options(state)
    entries = [
        _command(switch.title, switch.command, locale)
        for switch in switches
        if not switch.current and not switch.title.startswith("menu_series_")
    ]
    series = tuple(
        _command(switch.title, switch.command, locale)
        for switch in switches
        if switch.title.startswith("menu_series_") and not switch.current
    )
    if series:
        entries.append(MenuItem(text("menu_series_names", locale), children=series))
    if formats.supports(state, "number_format"):
        entries.append(_command("menu_number_format", "NumberFormat", locale))
    return MenuItem(text("menu_format", locale), children=tuple(entries))


def annotation_title(
    annotation: Annotation,
    data: ChartData,
    locale: str,
    fmt: Format | None = None,
    *,
    dates: bool = False,
) -> str:
    """The label of an annotation in menus and the sidebar, e.g. "Difference 2023 to 2025".

    ``dates``: the chart is a Gantt chart, whose value lines are date lines.
    """
    if annotation.kind == "axis_break":
        return text("menu_axis_break", locale, range=describe(annotation))
    if annotation.kind == "value_line" and dates:
        day = None if annotation.value is None else to_date(annotation.value)
        language = (fmt or Format()).language
        value = (
            text("menu_value_line_average", locale) if day is None else format_date(day, language)
        )
        return text("menu_date_line", locale, value=value)
    if annotation.kind == "value_line":
        value = (
            text("menu_value_line_average", locale)
            if annotation.value is None
            else format_value(annotation.value, fmt)
        )
        return text("menu_value_line", locale, value=value)
    key = (
        f"menu_{annotation.style}" if annotation.kind == "difference" else f"menu_{annotation.kind}"
    )
    title = text(
        key,
        locale,
        start=data.categories[annotation.start],
        end=data.categories[annotation.end],
    )
    if annotation.series is not None:
        title += f" ({data.series[annotation.series].name})"
    return title


def _actions(
    index: int, annotation: Annotation, locale: str, *, dates: bool = False
) -> tuple[MenuItem, ...]:
    change = f"ChangeAnnotation?index={index}&"
    actions: list[MenuItem] = []
    if annotation.kind == "axis_break":
        actions.append(_command("menu_change_break", "EditAxisBreak", locale))
    if annotation.kind == "value_line":
        key = "menu_change_date_line" if dates else "menu_change_value_line"
        actions.append(_command(key, f"EditValueLine?index={index}", locale))
    if annotation.kind == "difference":
        if annotation.label == "percent":
            actions.append(_command("menu_show_absolute", change + "label=absolute", locale))
        else:
            actions.append(_command("menu_show_percent", change + "label=percent", locale))
        if annotation.style == "bracket":
            actions.append(_command("menu_as_level", change + "style=level", locale))
        else:
            actions.append(_command("menu_as_bracket", change + "style=bracket", locale))
    actions.append(_command("menu_remove", f"RemoveAnnotation?index={index}", locale))
    return tuple(actions)
