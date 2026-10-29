"""The content of the LibreCharts sidebar panel (``lo/sidebar.py`` draws it).

Plain data, so what the panel offers for which selection is tested without LibreOffice. Every
button dispatches an ``org.librecharts:`` command, the same ones the menu and toolbar use.
"""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core import annotations as notes
from librecharts.core import format as formats
from librecharts.core import links, options, style
from librecharts.core.menu import PROTOCOL, annotation_title, arrange_items
from librecharts.core.messages import text
from librecharts.core.model import AnnotationKind, ChartState
from librecharts.core.picking import supports
from librecharts.core.scatter import parse_scatter


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
    """Sections top to bottom: insert, selected chart (``status``, edit, data link with
    ``link_status``, ``options``, ``format``), annotations, list, document (``update_all``,
    ``scheme``)."""

    insert: tuple[Button, ...]
    status: str
    edit: tuple[Button, ...]
    link_status: str
    link: tuple[Button, ...]
    options: tuple[Button, ...]
    format: tuple[Button, ...]
    add: tuple[Button, ...]
    rows: tuple[Row, ...]
    remove_all: Button
    update_all: Button
    schemes: tuple[Button, ...] = ()
    scheme_files: tuple[Button, ...] = ()
    scheme: str = ""
    elements: tuple[Button, ...] = ()
    arrange: tuple[Button, ...] = ()
    agenda: tuple[Button, ...] = ()


def content(
    state: ChartState | None,
    selected: bool,
    locale: str,
    scheme_name: str = style.DEFAULT.name,
    element_selected: bool = False,
    shapes_selected: int = 0,
    has_agenda: bool = False,
    agenda_slide: bool = False,
) -> Panel:
    """The panel for a selection: ``selected`` is whether a LibreCharts chart is selected and
    ``state`` its stored state (``None`` if the chart is orphaned or nothing is selected).

    ``scheme_name`` is the document's current colour scheme, for the Document section.
    ``element_selected`` is whether a Harvey ball or check mark is selected and ``shapes_selected``
    how many shapes are, for the Elements and Arrange sections. ``has_agenda`` is whether the
    presentation has an agenda and ``agenda_slide`` whether the current slide is one of its
    slides, for the Agenda section.
    """
    usable = selected and state is not None
    gantt = state is not None and state.kind == "gantt"
    linked = state is not None and state.link is not None
    rows: tuple[Row, ...] = ()
    if state is None:
        status = text("status_orphaned" if selected else "status_none", locale)
    else:
        data = notes.measured(state)
        kind = state.kind
        if kind == "mekko" and not state.percent:
            kind = "mekko_units"
        elif kind in ("column", "bar", "area") and state.percent:
            kind += "_percent"
        elif kind == "column" and state.lines:
            kind = "column_lines"
        elif kind == "pie" and state.doughnut:
            kind = "doughnut"
        elif kind == "scatter" and parse_scatter(state).bubbles:
            kind = "bubble"
        status = text(
            "status_gantt" if kind == "gantt" else "status_chart",
            locale,
            kind=text(f"kind_{kind}", locale),
            count=str(len(data.categories)),
        )
        if kind == "butterfly" and len(data.series) > 2:
            status += " " + text("status_butterfly_extra", locale)
        rows = tuple(
            Row(
                annotation_title(
                    annotation, data, locale, state.format, dates=state.kind == "gantt"
                ),
                f"RemoveAnnotation?index={index}",
            )
            for index, annotation in enumerate(state.annotations)
            if notes.drawable(annotation, data, state.kind)
        )
    return Panel(
        insert=(
            _button("insert_column", "InsertColumnChart", "insert", locale),
            _button("insert_bar", "InsertBarChart", "insert_bar", locale),
            _button("insert_line", "InsertLineChart", "insert_line", locale),
            _button("insert_area", "InsertAreaChart", "insert_area", locale),
            _button("insert_waterfall", "InsertWaterfallChart", "insert_waterfall", locale),
            _button("insert_mekko", "InsertMekkoChart", "insert_mekko", locale),
            _button("insert_pie", "InsertPieChart", "insert_pie", locale),
            _button("insert_scatter", "InsertScatterChart", "insert_scatter", locale),
            _button("insert_butterfly", "InsertButterflyChart", "insert_butterfly", locale),
            _button("insert_gantt", "InsertGanttChart", "insert_gantt", locale),
        ),
        status=status,
        edit=(
            _button(
                "menu_show_data" if linked else "menu_edit_data", "EditData", "edit", locale, usable
            ),
        ),
        link_status=links.status(state.link, locale) if state and state.link else "",
        link=_link(linked, usable, locale),
        options=_options(state, usable, locale),
        format=_format(state, usable, locale),
        add=(
            _button(
                "menu_add_difference",
                "PickAnnotation?kind=difference",
                "difference",
                locale,
                _can_annotate(state, usable, "difference"),
            ),
            _button(
                "menu_add_level",
                "PickAnnotation?kind=difference&style=level",
                "level",
                locale,
                _can_annotate(state, usable, "difference"),
            ),
            _button(
                "menu_add_cagr",
                "PickAnnotation?kind=cagr",
                "cagr",
                locale,
                _can_annotate(state, usable, "cagr"),
            ),
            _button(
                "menu_add_break",
                "AxisBreak",
                "axis_break",
                locale,
                _can_annotate(state, usable, "axis_break"),
            ),
            _button(
                "menu_add_date_line" if gantt else "menu_add_value_line",
                "ValueLine",
                "value_line",
                locale,
                _can_annotate(state, usable, "value_line"),
            ),
            *(
                (_button("menu_add_today_line", "TodayLine", "today_line", locale, usable),)
                if gantt
                else ()
            ),
        ),
        rows=rows,
        remove_all=_button("menu_remove_all", "RemoveAnnotations", "", locale, bool(rows)),
        update_all=_button("menu_update_all_links", "UpdateAllLinks", "", locale),
        schemes=tuple(
            _button(
                "",
                f"SetScheme?name={scheme.name}",
                "",
                locale,
                scheme.name != scheme_name,
                title=scheme.name,
            )
            for scheme in style.BUILT_INS
        ),
        scheme_files=(
            _button("panel_scheme_load", "LoadScheme", "", locale),
            _button("panel_scheme_save", "SaveScheme", "", locale),
        ),
        scheme=scheme_name,
        elements=(
            _button("insert_harvey", "InsertElement?harvey=50", "", locale),
            _button("insert_check", "InsertElement?check=tick", "", locale),
            _button("menu_element_next", "SetElement?next=1", "", locale, element_selected),
        ),
        arrange=tuple(
            Button(
                item.title,
                item.command,
                "",
                shapes_selected >= 2
                and (shapes_selected == 2 or not item.command.endswith("op=swap")),
            )
            for item in arrange_items(locale)
        ),
        agenda=(
            # always enabled: after its main slide was deleted, an agenda is inserted again
            _button("menu_insert_agenda", "InsertAgenda", "", locale),
            _button(
                "menu_start_chapter", "StartChapter", "", locale, has_agenda and not agenda_slide
            ),
            _button("menu_update_agenda", "UpdateAgenda", "", locale, has_agenda),
        ),
    )


def _link(linked: bool, usable: bool, locale: str) -> tuple[Button, ...]:
    if not linked:
        return (_button("menu_link_data", "LinkData", "", locale, usable),)
    return (
        _button("menu_update_link", "UpdateLink", "", locale, usable),
        _button("menu_change_link", "LinkData", "", locale, usable),
        _button("menu_open_source", "OpenSource", "", locale, usable),
        _button("menu_remove_link", "RemoveLink", "", locale, usable),
    )


def _options(state: ChartState | None, usable: bool, locale: str) -> tuple[Button, ...]:
    if state is None:
        return ()
    variants = options.variants(state)
    if state.kind == "mekko":  # the Mekko keeps a single toggle button
        variants = tuple(switch for switch in variants if not switch.current)
    buttons = tuple(
        _button(switch.title, switch.command, "", locale, usable and not switch.current)
        for switch in variants
    )
    toggle = options.sort_toggle(state)
    if toggle is not None:
        buttons += (_button(toggle.title, toggle.command, "", locale, usable),)
    return buttons


def _format(state: ChartState | None, usable: bool, locale: str) -> tuple[Button, ...]:
    if state is None:
        return ()
    buttons = tuple(
        _button(switch.title, switch.command, "", locale, usable)
        for switch in formats.format_options(state)
        if not switch.current
    )
    buttons += (
        _button("menu_copy_format", "CopyChartFormat", "", locale),
        _button("menu_apply_format", "ApplyChartFormat", "", locale),
    )
    if state.scale_group is not None:
        buttons += (_button("menu_remove_same_scale", "RemoveSameScale", "", locale, usable),)
    if formats.supports(state, "number_format"):
        buttons += (_button("menu_number_format", "NumberFormat", "", locale, usable),)
    return buttons


def _can_annotate(state: ChartState | None, usable: bool, kind: AnnotationKind) -> bool:
    return usable and state is not None and supports(state, kind)


def _button(
    key: str,
    command: str,
    icon: str,
    locale: str,
    enabled: bool = True,
    *,
    title: str | None = None,
) -> Button:
    return Button(text(key, locale) if title is None else title, PROTOCOL + command, icon, enabled)
