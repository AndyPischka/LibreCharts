"""The LibreCharts entries in the context menu of a selected chart (M4 plan, "Interaction").

Built as plain data, so its contents are tested without LibreOffice; ``lo/contextmenu.py`` turns
it into menu entries. Every entry dispatches an ``org.librecharts:`` command.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core.axis_break import describe
from librecharts.core.datasheet import ChartData, parse
from librecharts.core.messages import text
from librecharts.core.model import Annotation, ChartState
from librecharts.core.picking import supports

PROTOCOL = "org.librecharts:"


@dataclass(frozen=True, slots=True)
class MenuItem:
    """An entry: a command, a submenu (``children``), or a separator (no title)."""

    title: str = ""
    command: str = ""
    children: tuple[MenuItem, ...] = ()


SEPARATOR = MenuItem()


def chart_menu(state: ChartState, locale: str) -> MenuItem:
    """The "LibreCharts" submenu for a chart with ``state``."""
    items = [MenuItem(text("menu_edit_data", locale), PROTOCOL + "EditData")]
    if supports(state, "difference"):
        items += [
            SEPARATOR,
            _command("menu_add_difference", "PickAnnotation?kind=difference", locale),
            _command("menu_add_level", "PickAnnotation?kind=difference&style=level", locale),
            _command("menu_add_cagr", "PickAnnotation?kind=cagr", locale),
            _command("menu_add_break", "AxisBreak", locale),
        ]
    data = parse(state)
    shown = [
        (index, annotation)
        for index, annotation in enumerate(state.annotations)
        if notes.drawable(annotation, data, state.kind)
    ]
    if shown:
        items.append(SEPARATOR)
        items += [
            MenuItem(_title(annotation, data, locale), children=_actions(index, annotation, locale))
            for index, annotation in shown
        ]
        items.append(_command("menu_remove_all", "RemoveAnnotations", locale))
    return MenuItem("LibreCharts", children=tuple(items))


def _command(key: str, command: str, locale: str) -> MenuItem:
    return MenuItem(text(key, locale), PROTOCOL + command)


def _title(annotation: Annotation, data: ChartData, locale: str) -> str:
    if annotation.kind == "axis_break":
        return text("menu_axis_break", locale, range=describe(annotation))
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


def _actions(index: int, annotation: Annotation, locale: str) -> tuple[MenuItem, ...]:
    change = f"ChangeAnnotation?index={index}&"
    actions: list[MenuItem] = []
    if annotation.kind == "axis_break":
        actions.append(_command("menu_change_break", "EditAxisBreak", locale))
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
