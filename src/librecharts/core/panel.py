"""The content of the LibreCharts sidebar panel (``lo/sidebar.py`` draws it).

Plain data, so what the panel offers for which selection is tested without LibreOffice. Every
button dispatches an ``org.librecharts:`` command, the same ones the menu and toolbar use.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core.datasheet import parse
from librecharts.core.menu import PROTOCOL, annotation_title
from librecharts.core.messages import text
from librecharts.core.model import ChartState
from librecharts.core.picking import supports


@dataclass(frozen=True, slots=True)
class Button:
    """A panel button: ``icon`` is the file name stem in ``extension/images`` (16 px variant)."""

    title: str
    command: str
    icon: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Row:
    """An annotation of the selected chart, with the command that removes it."""

    title: str
    remove: str


@dataclass(frozen=True, slots=True)
class Panel:
    """Sections top to bottom: insert, selected chart (``status``, edit), annotations, list."""

    insert: tuple[Button, ...]
    status: str
    edit: tuple[Button, ...]
    add: tuple[Button, ...]
    rows: tuple[Row, ...]
    remove_all: Button


def content(state: ChartState | None, selected: bool, locale: str) -> Panel:
    """The panel for a selection: ``selected`` is whether a LibreCharts chart is selected and
    ``state`` its stored state (``None`` if the chart is orphaned or nothing is selected)."""
    usable = selected and state is not None
    rows: tuple[Row, ...] = ()
    if state is None:
        status = text("status_orphaned" if selected else "status_none", locale)
    else:
        data = parse(state)
        status = text(
            "status_chart",
            locale,
            kind=text(f"kind_{state.kind}", locale),
            count=str(len(data.categories)),
        )
        rows = tuple(
            Row(annotation_title(annotation, data, locale), f"RemoveAnnotation?index={index}")
            for index, annotation in enumerate(state.annotations)
            if notes.drawable(annotation, data, state.kind)
        )
    return Panel(
        insert=(
            _button("insert_column", "InsertColumnChart", "insert", locale),
            _button("insert_bar", "InsertBarChart", "insert_bar", locale),
            _button("insert_waterfall", "InsertWaterfallChart", "insert_waterfall", locale),
            _button("insert_mekko", "InsertMekkoChart", "insert_mekko", locale),
        ),
        status=status,
        edit=(_button("menu_edit_data", "EditData", "edit", locale, usable),),
        add=(
            _button(
                "menu_add_difference",
                "PickAnnotation?kind=difference",
                "difference",
                locale,
                _can_annotate(state, usable),
            ),
            _button(
                "menu_add_level",
                "PickAnnotation?kind=difference&style=level",
                "level",
                locale,
                _can_annotate(state, usable),
            ),
            _button(
                "menu_add_cagr",
                "PickAnnotation?kind=cagr",
                "cagr",
                locale,
                _can_annotate(state, usable),
            ),
            _button(
                "menu_add_break", "AxisBreak", "axis_break", locale, _can_annotate(state, usable)
            ),
        ),
        rows=rows,
        remove_all=_button("menu_remove_all", "RemoveAnnotations", "", locale, bool(rows)),
    )


def _can_annotate(state: ChartState | None, usable: bool) -> bool:
    return usable and state is not None and supports(state, "difference")


def _button(key: str, command: str, icon: str, locale: str, enabled: bool = True) -> Button:
    return Button(text(key, locale), PROTOCOL + command, icon, enabled)
