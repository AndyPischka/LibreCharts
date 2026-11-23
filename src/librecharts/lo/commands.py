# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Menu commands, called by extension/entry.py with the frame the command was invoked in."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

import uno

from librecharts import api
from librecharts.core import (
    annotations,
    colorblind,
    csvexport,
    deck_export,
    elements,
    gantt,
    gantt_import,
    options,
    style,
)
from librecharts.core import arrange as core_arrange
from librecharts.core import audit as core_audit
from librecharts.core import calendar as working_calendar
from librecharts.core import designcheck as core_design
from librecharts.core import format as formats
from librecharts.core import graphics as core_graphics
from librecharts.core import importdata as core_import
from librecharts.core import labels as core_labels
from librecharts.core import links as core_links
from librecharts.core import matrix as core_matrix
from librecharts.core import notes as core_notes
from librecharts.core import samescale as core_samescale
from librecharts.core import table as core_table
from librecharts.core import templates as core_templates
from librecharts.core.deck import DeckError
from librecharts.core.layout.chart import layout_chart
from librecharts.core.messages import text
from librecharts.core.model import (
    Annotation,
    AnnotationKind,
    ChartState,
    MatrixSpec,
    TableSpec,
    Trend,
)
from librecharts.core.picking import PickSession, annotation_kind, supports
from librecharts.core.state_io import StateError
from librecharts.lo import agenda as lo_agenda
from librecharts.lo import (
    alttextall,
    auditdialog,
    axisdialog,
    calendardialog,
    chart,
    dataimport,
    datasheet,
    designcheck,
    formatdialog,
    icondialog,
    labelpick,
    labels,
    linkdialog,
    links,
    matrixdialog,
    pick,
    resize,
    samescale,
    scheme,
    store,
    tabledialog,
    textdialog,
    themedialog,
    trenddialog,
    ui,
)
from librecharts.lo import arrange as lo_arrange
from librecharts.lo import audit as lo_audit
from librecharts.lo import elements as lo_elements
from librecharts.lo import (
    graphics as lo_graphics,
)
from librecharts.lo import (
    templates as lo_templates,
)
from librecharts.lo.datasheet import OrphanedChartError, open_datasheet

# The format copied by "Copy chart format", shared by the menu and the sidebar in this process.
_format_slot: ChartState | None = None


def insert_column_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_column_chart)


def insert_bar_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_bar_chart)


def insert_line_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_line_chart)


def insert_area_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_area_chart)


def insert_waterfall_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_waterfall_chart)


def insert_mekko_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_mekko_chart)


def insert_pie_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_pie_chart)


def insert_scatter_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_scatter_chart)


def insert_butterfly_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_butterfly_chart)


def insert_gantt_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_gantt_chart)


def insert_dumbbell_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_dumbbell_chart)


def insert_bullet_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_bullet_chart)


def insert_funnel_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_funnel_chart)


def insert_boxplot_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_boxplot_chart)


def insert_table_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_table_chart)


def insert_matrix_chart(ctx: Any, frame: Any) -> None:
    _insert(ctx, frame, chart.insert_matrix_chart)


def _insert(ctx: Any, frame: Any, insert: Any) -> None:
    controller = frame.getController()
    doc = controller.getModel()
    group = insert(doc, controller.getCurrentPage(), locale=ui.ui_locale(ctx))
    resize.watch(
        doc
    )  # normally done by the document-open job; covers a freshly installed extension
    controller.select(group)


def insert_graphic(ctx: Any, frame: Any, query: str) -> None:
    """Insert a process, chevron, pyramid or icon graphic (M26); one undo step."""
    locale = ui.ui_locale(ctx)
    try:
        graphic, labels = core_graphics.from_query(query)
    except ValueError:
        ui.show_info(ctx, frame, text("graphic_unsupported", locale))
        return
    controller = frame.getController()
    doc = controller.getModel()
    controller.select(lo_graphics.insert(doc, controller.getCurrentPage(), graphic, labels))
    resize.watch(doc)


def insert_icon(ctx: Any, frame: Any, query: str) -> None:
    """Pick one built-in icon and insert it (M26); one undo step."""
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    name = args.get("name", "") or icondialog.ask(ctx, frame)
    if not name:
        return
    try:
        graphic = core_graphics.Graphic("icon", icon=name)
    except ValueError:
        ui.show_info(ctx, frame, text("graphic_unsupported", ui.ui_locale(ctx)))
        return
    controller = frame.getController()
    controller.select(
        lo_graphics.insert(controller.getModel(), controller.getCurrentPage(), graphic)
    )


def change_graphic(ctx: Any, frame: Any, query: str) -> None:
    """Add/remove a step or switch a graphic's direction (M26); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    selection = controller.getSelection()
    group = selection if selection is not None and hasattr(selection, "Name") else None
    graphic = lo_graphics.find(group) if group is not None else None
    if graphic is None:
        ui.show_info(ctx, frame, text("graphic_not_selected", locale))
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        if args.get("op") == "direction":
            if graphic.kind == "pyramid":
                changed = replace(graphic, inverted=not graphic.inverted)
            else:
                changed = replace(graphic, horizontal=not graphic.horizontal)
        elif args.get("op") in ("add", "remove"):
            step = 1 if args["op"] == "add" else -1
            changed = replace(graphic, steps=graphic.steps + step)
        else:
            raise ValueError(args)
    except ValueError:
        ui.show_info(ctx, frame, text("graphic_unsupported", locale))
        return
    lo_graphics.change(controller.getModel(), group, changed)


def insert_element(ctx: Any, frame: Any, query: str) -> None:
    """Insert a Harvey ball or check mark (``harvey=50`` or ``check=tick``); one undo step."""
    try:
        element = elements.parse_query(query)
    except ValueError:
        ui.show_info(ctx, frame, text("element_unsupported", ui.ui_locale(ctx)))
        return
    controller = frame.getController()
    doc = controller.getModel()
    resize.watch(doc)
    controller.select(lo_elements.insert(doc, controller.getCurrentPage(), element))


def set_element(ctx: Any, frame: Any, query: str) -> None:
    """Change the state of the selected elements (``harvey=75``, ``check=cross`` or ``next=1``,
    which cycles each one on); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    selected = lo_elements.selected_elements(controller)
    if not selected:
        ui.show_info(ctx, frame, text("select_element", locale))
        return
    try:
        changes = {
            group: (
                elements.following(element)
                if query.startswith("next")
                else elements.parse_query(query)
            )
            for group, element in selected
        }
    except ValueError:
        ui.show_info(ctx, frame, text("element_unsupported", locale))
        return
    # A ball cannot become a tick: a state of the other kind leaves that element as it is.
    changes = {g: e for g, e in changes.items() if e.kind == lo_elements.element_of(g).kind}  # type: ignore[union-attr]
    if changes:
        lo_elements.change(controller.getModel(), changes)


def arrange(ctx: Any, frame: Any, query: str) -> None:
    """Arrange the selected shapes: ``op=width|height|size|swap`` or ``op=grid&columns=3&gap=500``
    (``gap`` in 1/100 mm); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    shapes = lo_arrange.selected_shapes(controller)
    if len(shapes) < 2:
        ui.show_info(ctx, frame, text("arrange_need_two", locale))
        return
    rects = [lo_arrange.rect_of(shape) for shape in shapes]
    op = args.get("op", "")
    try:
        if op == "width":
            wanted = core_arrange.same_width(rects)
        elif op == "height":
            wanted = core_arrange.same_height(rects)
        elif op == "size":
            wanted = core_arrange.same_size(rects)
        elif op == "grid":
            wanted = core_arrange.grid(
                rects, int(args.get("columns", "")), int(args.get("gap", lo_arrange.DEFAULT_GAP))
            )
        elif op == "swap":
            if len(shapes) != 2:
                ui.show_info(ctx, frame, text("arrange_need_exactly_two", locale))
                return
            wanted = list(core_arrange.swap(rects[0], rects[1]))
        elif op == "distribute":
            wanted = core_arrange.distribute(rects, args.get("axis", "h"), args.get("mode", "gaps"))
        elif op == "align":
            wanted = core_arrange.align(rects, args.get("edge", "left"))
        elif op == "align-slide":
            page = controller.getCurrentPage()
            wanted = core_arrange.align_slide(
                rects,
                args.get("edge", "left"),
                page.Width,
                page.Height,
                int(args.get("margin", "0")),
            )
        else:
            raise ValueError(op)
    except ValueError:
        ui.show_info(ctx, frame, text("arrange_unsupported", locale))
        return
    lo_arrange.apply(controller.getModel(), shapes, wanted)


def insert_agenda(ctx: Any, frame: Any) -> None:
    _agenda(ctx, frame, lo_agenda.insert)


def start_chapter(ctx: Any, frame: Any) -> None:
    _agenda(ctx, frame, lo_agenda.start_chapter)


def update_agenda(ctx: Any, frame: Any) -> None:
    _agenda(ctx, frame, lambda doc, _controller, locale: lo_agenda.update(doc, locale))


def _agenda(ctx: Any, frame: Any, command: Callable[[Any, Any, str], None]) -> None:
    """Run an agenda command on the presentation of ``frame``; tell the user if it cannot run."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    try:
        command(controller.getModel(), controller, locale)
    except lo_agenda.Refused as refused:
        ui.show_info(ctx, frame, text(refused.key, locale))


def edit_data(ctx: Any, frame: Any) -> None:
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    group = selected_chart(controller)
    if group is None:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return
    if store.claim(controller.getModel(), group) is None:
        ui.show_info(ctx, frame, text("orphaned_chart", locale))
        return
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    # The data sheet follows the presentation's visibility: a document opened hidden (macros,
    # tests) must not pop up a Calc window.
    hidden = not frame.getContainerWindow().isVisible()
    load_args = (ui.prop("Hidden", True),) if hidden else ()
    try:
        open_datasheet(desktop, controller.getModel(), group, locale, load_args)
    except OrphanedChartError:
        ui.show_info(ctx, frame, text("orphaned_chart", locale))
    except StateError as exc:
        ui.show_info(ctx, frame, text("corrupt_chart", locale, detail=str(exc)))


def link_data(ctx: Any, frame: Any, query: str) -> None:
    """Link the chart to a range of a spreadsheet file (ADR 0020); one undo step.

    Asks with a dialog; scripts and tests pass ``url=...&sheet=...&range=...`` instead (``url``
    may also be a system path, ``sheet`` is left out for a named range).
    """
    found = _link_chart(ctx, frame)
    if found is None:
        return
    doc, frame, group, state = found
    if not query:
        linkdialog.request(ctx, frame, group, state)
        return
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    checked = core_links.target(args.get("sheet", ""), args.get("range", ""))
    if isinstance(checked, str):
        ui.show_info(ctx, frame, text(checked, locale, range=args.get("range", "")))
        return
    try:
        linked = links.link(
            ctx,
            doc,
            state,
            links.as_url(args.get("url", "")),
            *checked,
            auto=args.get("auto") == "true",
        )
    except links.LinkError as exc:
        ui.show_info(ctx, frame, exc.message(locale))
        return
    chart.redraw(doc, group, linked)
    _refresh_datasheet(doc, group)


def share_link(ctx: Any, frame: Any, query: str) -> None:
    """Link every selected chart to the same range (M28); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    groups = selected_charts(controller)
    if not groups:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return
    doc = controller.getModel()
    states = _claimed_states(ctx, frame, doc, groups, locale)
    if states is None:
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    checked = core_links.target(args.get("sheet", ""), args.get("range", ""))
    if isinstance(checked, str):
        ui.show_info(ctx, frame, text(checked, locale, range=args.get("range", "")))
        return
    changes: dict[Any, ChartState] = {}
    try:
        for group, state in states:
            changes[group] = links.link(
                ctx,
                doc,
                state,
                links.as_url(args.get("url", "")),
                *checked,
                auto=args.get("auto") == "true",
            )
    except links.LinkError as exc:
        ui.show_info(ctx, frame, exc.message(locale))
        return
    chart.apply_changes(doc, changes)


def update_link(ctx: Any, frame: Any) -> None:
    """Update the selected linked charts from their sources; one undo step."""
    frame = _presentation_frame(frame)
    doc = frame.getController().getModel()
    locale = ui.ui_locale(ctx)
    groups = selected_charts(frame.getController())
    if not groups:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return
    states = _claimed_states(ctx, frame, doc, groups, locale)
    if states is None:
        return
    ids = {
        chart_id
        for group, state in states
        if state.link is not None and (chart_id := store.chart_id_of(group)) is not None
    }
    if not ids:
        ui.show_info(ctx, frame, text("link_not_linked", locale))
        return
    _update_links(ctx, frame, doc, ids)


def update_all_links(ctx: Any, frame: Any) -> None:
    """Update every linked chart of the presentation; one undo step, each source opened once."""
    doc = frame.getController().getModel()
    links.withdraw_offer(doc)
    _update_links(ctx, frame, doc, None)


def _update_links(ctx: Any, frame: Any, doc: Any, ids: set[str] | None) -> None:
    """Update the linked charts with ids in ``ids`` (or all) and tell the user about problems."""
    message = api.update_links(ctx, doc, ids, ui.ui_locale(ctx))
    if message:
        ui.show_info(ctx, frame, message)


def build_deck(ctx: Any, frame: Any, query: str) -> None:
    """Build a deck from a template and a specification (M18, ADR 0028); the macro API's build.

    ``org.librecharts:BuildDeck?template=<url>&data=<url>&out=<url>`` (percent-encoded file URLs or
    system paths). The report, or the reason nothing was built, goes to a message box; without a
    window (headless, hidden documents) it is printed.
    """
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    locale = ui.ui_locale(ctx)
    try:
        report = api.build_deck(
            ctx, args.get("template", ""), args.get("data", ""), args.get("out", ""), locale
        )
    except DeckError as exc:
        ui.tell(ctx, frame, exc.message(locale))
        return
    ui.tell(ctx, frame, report)


def open_source(ctx: Any, frame: Any) -> None:
    """Open the linked chart's source and select the linked range in it."""
    found = _link_chart(ctx, frame)
    if found is None:
        return
    doc, frame, _, state = found
    locale = ui.ui_locale(ctx)
    if state.link is None:
        ui.show_info(ctx, frame, text("link_not_linked", locale))
        return
    hidden = not frame.getContainerWindow().isVisible()
    try:
        links.show_source(ctx, doc, state.link, hidden)
    except links.LinkError as exc:
        ui.show_info(ctx, frame, exc.message(locale))


def remove_link(ctx: Any, frame: Any) -> None:
    """Give the linked chart its own data again (the last fetched values); one undo step."""
    found = _link_chart(ctx, frame)
    if found is None:
        return
    doc, _, group, state = found
    if state.link is not None:
        chart.redraw(doc, group, replace(state, link=None))
        _refresh_datasheet(doc, group)


def _link_chart(ctx: Any, frame: Any) -> tuple[Any, Any, Any, ChartState] | None:
    """The chart a link command is for, as (presentation, its frame, group, state)."""
    frame = _presentation_frame(frame)
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return None
    group, state = found
    return frame.getController().getModel(), frame, group, state


def _presentation_frame(frame: Any) -> Any:
    """``frame``, or for a command from a data sheet's info bar the frame of its presentation,
    with the sheet's chart selected there."""
    owner = datasheet.owner(frame.getController().getModel())
    if owner is None:
        return frame
    doc, group = owner
    doc.getCurrentController().select(group)
    return doc.getCurrentController().getFrame()


def _refresh_datasheet(doc: Any, group: Any) -> None:
    chart_id = store.chart_id_of(group)
    if chart_id is not None:
        datasheet.refresh(doc, chart_id)


def import_gantt_csv(ctx: Any, frame: Any, query: str) -> None:
    """Import a CSV file into the selected Gantt chart's data sheet; one undo step."""
    _import_gantt(ctx, frame, query, "csv")


def import_gantt_project(ctx: Any, frame: Any, query: str) -> None:
    """Import a ProjectLibre `.pod` or MS Project XML file; one undo step."""
    _import_gantt(ctx, frame, query, "project")


def _import_gantt(ctx: Any, frame: Any, query: str, kind: str) -> None:
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if state.kind != "gantt":
        ui.show_info(ctx, frame, text("import_not_gantt", locale))
        return
    if state.link is not None:
        ui.show_info(ctx, frame, text("import_linked", locale))
        return
    url = _query_arg(query, "url")
    if url:
        url = links.as_url(url)
    else:
        title = text("import_csv_title" if kind == "csv" else "import_project_title", locale)
        url = _pick_import_file(ctx, title, kind, locale)
        if url is None:
            return
    try:
        path = uno.fileUrlToSystemPath(url)
    except Exception:
        ui.show_info(ctx, frame, text("import_failed", locale, detail=url))
        return
    try:
        data = Path(path).read_bytes()
        if kind == "csv":
            table = gantt_import.parse_csv(_text_of(data), state.format.language)
        else:
            table = gantt_import.parse_msppi(data, state.format.language)
        if not table.rows:
            ui.show_info(ctx, frame, text("import_empty", locale))
            return
        imported = gantt_import.state_from_table(table, state)
        if kind == "project":
            calendar = gantt_import.calendar_from_msppi(data)
            if calendar is not None:
                imported = replace(imported, calendar=calendar)
    except (OSError, gantt_import.GanttImportError) as exc:
        detail = (
            text(exc.key, locale) if isinstance(exc, gantt_import.GanttImportError) else str(exc)
        )
        ui.show_info(ctx, frame, text("import_failed", locale, detail=detail))
        return
    chart.redraw(frame.getController().getModel(), group, imported)
    _refresh_datasheet(frame.getController().getModel(), group)
    ui.show_info(ctx, frame, text("import_done", locale, count=str(len(table.rows))))


def _query_arg(query: str, name: str) -> str:
    values = parse_qs(query).get(name, [])
    return values[-1] if values else ""


def _text_of(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _pick_import_file(ctx: Any, title: str, kind: str, locale: str) -> str | None:
    picker = ctx.ServiceManager.createInstanceWithContext("com.sun.star.ui.dialogs.FilePicker", ctx)
    picker.setTitle(title)
    if kind == "data":
        label, pattern = text("import_data_filter", locale), "*.csv;*.txt;*.tsv;*.ods;*.xlsx"
    else:
        label = text("import_csv_filter" if kind == "csv" else "import_project_filter", locale)
        pattern = "*.csv;*.txt;*.tsv" if kind == "csv" else "*.pod;*.xml"
    picker.appendFilter(label, pattern)
    picker.setCurrentFilter(label)
    if picker.execute() != 1:  # com.sun.star.ui.dialogs.ExecutableDialogResults.OK
        return None
    files = picker.getFiles()
    return str(files[0]) if files else None


def add_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Add the annotation described by ``query`` (see ``annotations.from_query``) to the selected
    chart; one undo step. Used by tests and scripts; users pick columns instead."""
    annotation = annotations.from_query(query)
    found = _annotatable_chart(ctx, frame, annotation.kind)
    if found is None:
        return
    group, _ = found
    try:
        chart.add_annotation(frame.getController().getModel(), group, annotation)
    except ValueError:
        # the chart state rejects the annotation (e.g. a median mode on a Gantt date line)
        ui.show_info(ctx, frame, text("annotation_unsupported", ui.ui_locale(ctx)))


def pick_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Start pick mode for the annotation kind (and style) in ``query`` on the selected chart."""
    session = PickSession.from_query(query)
    found = _annotatable_chart(ctx, frame, annotation_kind(session.kind))
    if found is not None:
        group, state = found
        pick.start(ctx, frame, group, state, session)


def axis_break(ctx: Any, frame: Any) -> None:
    """Ask for the axis break of the selected chart (a dialog), then add or change it."""
    found = _annotatable_chart(ctx, frame, "axis_break")
    if found is not None:
        group, state = found
        axisdialog.request(ctx, frame, group, state)


def change_chart(ctx: Any, frame: Any, query: str) -> None:
    """Change a chart option such as ``percent=false`` (see ``options.changed``); one undo step."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    try:
        changed = options.changed(state, query)
    except ValueError:
        ui.show_info(ctx, frame, text("option_unsupported", ui.ui_locale(ctx)))
        return
    if changed != state:
        chart.redraw(frame.getController().getModel(), group, changed)


def change_format(ctx: Any, frame: Any, query: str) -> None:
    """Change a format option such as ``axis=true`` (see ``format.changed``); one undo step."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    try:
        changed = formats.settled(state, state.format, query)
    except ValueError:
        ui.show_info(ctx, frame, text("option_unsupported", ui.ui_locale(ctx)))
        return
    if changed != state.format:
        chart.redraw(frame.getController().getModel(), group, replace(state, format=changed))


def change_focus(ctx: Any, frame: Any, query: str) -> None:
    """Change the focus sets from the compact UI form ``series=2&on=true`` (M22)."""
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    kind = "series" if "series" in args else ("category" if "category" in args else "")
    if not kind:
        change_chart(ctx, frame, "focus=none" if args.get("clear") == "true" else query)
        return
    args["focus"] = kind
    args["index"] = args.pop(kind)
    change_chart(ctx, frame, urlencode(args))


def set_label(ctx: Any, frame: Any, query: str, command: str = "SetLabel") -> None:
    """Hide, retitle or reset one label (M22); one undo step.

    Without a query the label picker starts: the user clicks a label, then the text dialog asks
    (``SetLabelText``) or the label is hidden/reset at once.
    """
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    if not query:
        labelpick.start(ctx, frame, group, command)
        return
    try:
        changed = core_labels.override(state, query, command=command)
    except ValueError:
        ui.show_info(ctx, frame, text("label_unsupported", ui.ui_locale(ctx)))
        return
    if changed != state:
        chart.redraw(frame.getController().getModel(), group, changed)


def set_source(ctx: Any, frame: Any, query: str) -> None:
    """Set or clear the chart's source line (M22); one undo step."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if not query:
        value = textdialog.ask_text(ctx, frame, "source_title", "source_label", state.source)
        if value is None:
            return
        query = urlencode({"text": value})
    try:
        changed = core_notes.changed(state, query, "SetSource")
    except ValueError:
        ui.show_info(ctx, frame, text("note_unsupported", locale))
        return
    if changed != state:
        chart.redraw(frame.getController().getModel(), group, changed)


def add_note(ctx: Any, frame: Any, query: str) -> None:
    """Add a free callout at a fraction of the chart box (M22); one undo step."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if not query:
        value = textdialog.ask_text(ctx, frame, "note_title", "note_label", "")
        if value is None:
            return
        query = urlencode({"text": value, "x": "0.1", "y": "0.1"})
    try:
        changed = core_notes.changed(state, query, "AddNote")
    except ValueError:
        ui.show_info(ctx, frame, text("note_unsupported", locale))
        return
    chart.redraw(frame.getController().getModel(), group, changed)


def remove_note(ctx: Any, frame: Any, query: str) -> None:
    """Remove the note at ``index=...`` (M22); one undo step."""
    _change_note(ctx, frame, query, "RemoveNote")


def move_note(ctx: Any, frame: Any, query: str) -> None:
    """Move the note at ``index=...`` to ``x`` and ``y`` (M22); one undo step."""
    _change_note(ctx, frame, query, "MoveNote")


def _change_note(ctx: Any, frame: Any, query: str, command: str) -> None:
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    try:
        changed = core_notes.changed(state, query, command)
    except ValueError:
        ui.show_info(ctx, frame, text("note_unsupported", ui.ui_locale(ctx)))
        return
    if changed != state:
        chart.redraw(frame.getController().getModel(), group, changed)


def move_labels(ctx: Any, frame: Any) -> None:
    """Enter the selected chart so that its value labels and totals can be dragged (ADR 0023)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    if not core_labels.movable(state):
        ui.show_info(ctx, frame, text("option_unsupported", ui.ui_locale(ctx)))
        return
    labels.start(ctx, frame, group)


def reset_labels(ctx: Any, frame: Any) -> None:
    """Put every label of the selected chart back where the layout puts it; one undo step."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    if state.labels:
        chart.redraw(frame.getController().getModel(), group, replace(state, labels=()))


def axes(ctx: Any, frame: Any, query: str) -> None:
    """Open the axis dialog, or apply its fields from ``query``; one undo step (M23)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if not query:
        axisdialog.request_axes(ctx, frame, group, state)
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        fmt = formats.axes(state.format, args)
    except ValueError:
        ui.show_info(ctx, frame, text("axis_invalid", locale))
        return
    if (
        fmt.axis_min is not None
        and fmt.axis_min > 0
        and state.kind not in ("line", "scatter")
        and not ui.ask(ctx, frame, text("axis_cut_warning", locale))
    ):
        return
    try:
        changed = replace(state, format=fmt)
        # Constructing the state validates the bounds and titles.
        if fmt.axis_scale == "log":
            layout_chart(changed, 4000, 4000)
    except ValueError:
        ui.show_info(ctx, frame, text("axis_invalid", locale))
        return
    if changed != state:
        chart.redraw(frame.getController().getModel(), group, changed)


def add_trendline(ctx: Any, frame: Any, query: str) -> None:
    """Add or replace the trendline of one series; one undo step (M23)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if not query:
        trenddialog.request(ctx, frame, group, state, None)
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        series = int(args["series"])
        trend = Trend(
            series,
            args.get("kind", "linear"),  # pyright: ignore[reportArgumentType]
            int(args.get("forecast", "0")),
            args.get("r2", "true") != "false",
            args.get("equation", "false") == "true",
        )
    except (KeyError, ValueError):
        ui.show_info(ctx, frame, text("trend_invalid", locale))
        return
    if series >= len(state.values) - 1:
        ui.show_info(ctx, frame, text("trend_invalid", locale))
        return
    changed = replace(
        state, trends=(*(item for item in state.trends if item.series != series), trend)
    )
    try:
        layout_chart(changed, 4000, 4000)
    except ValueError:
        ui.show_info(ctx, frame, text("trend_invalid", locale))
        return
    chart.redraw(frame.getController().getModel(), group, changed)


def remove_trendline(ctx: Any, frame: Any, query: str) -> None:
    """Remove the trendline of ``series=...``; one undo step (M23)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        series = int(args["series"])
    except (KeyError, ValueError):
        return
    trends = tuple(item for item in state.trends if item.series != series)
    if trends != state.trends:
        chart.redraw(frame.getController().getModel(), group, replace(state, trends=trends))


def number_format(ctx: Any, frame: Any) -> None:
    """Ask for the number format of the selected chart (a dialog), then apply it."""
    found = _annotatable_chart(ctx, frame, None)
    if found is not None:
        group, state = found
        formatdialog.request_number(ctx, frame, group, state)


def value_line(ctx: Any, frame: Any) -> None:
    """Ask for a value line (a target, the average or the median) and add it; one undo step."""
    found = _annotatable_chart(ctx, frame, "value_line")
    if found is not None:
        group, state = found
        formatdialog.request_value_line(ctx, frame, group, state, None)


def today_line(ctx: Any, frame: Any) -> None:
    """Add a date line at today's date to the selected Gantt chart; one undo step.

    The date is filled in once: the line does not move on later days (a layout depends on the
    stored state only).
    """
    found = _annotatable_chart(ctx, frame, "value_line")
    if found is None:
        return
    group, state = found
    if state.kind != "gantt":
        ui.show_info(ctx, frame, text("option_unsupported", ui.ui_locale(ctx)))
        return
    today = float(gantt.serial(datetime.date.today()))
    chart.add_annotation(
        frame.getController().getModel(), group, Annotation("value_line", 0, 0, value=today)
    )


def working_days(ctx: Any, frame: Any, query: str) -> None:
    """Set the working days of the selected Gantt chart; one undo step.

    Without a query the dialog asks for weekdays and holidays; scripts and tests pass
    ``working=1,2,3,4,5&holidays=2026-12-25`` (ISO weekdays, 1 = Monday).
    """
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if state.kind != "gantt":
        ui.show_info(ctx, frame, text("option_unsupported", locale))
        return
    if not query:
        calendardialog.request(ctx, frame, group, state)
        return
    try:
        chosen = working_calendar.changed(state.calendar, query, state.format.language)
    except ValueError:
        ui.show_info(ctx, frame, text("option_unsupported", locale))
        return
    if chosen != state.calendar:
        chart.redraw(frame.getController().getModel(), group, replace(state, calendar=chosen))


def edit_value_line(ctx: Any, frame: Any, query: str) -> None:
    """Change the value line at ``index=...`` through the same dialog; one undo step."""
    found = _annotatable_chart(ctx, frame, "value_line")
    if found is None:
        return
    group, state = found
    index = _index(query)
    if index is None or not 0 <= index < len(state.annotations):
        return
    if state.annotations[index].kind != "value_line":
        return
    formatdialog.request_value_line(ctx, frame, group, state, index)


def edit_bracket_text(ctx: Any, frame: Any, query: str) -> None:
    """Change the text of the group bracket at ``index=...`` through a dialog; one undo step."""
    found = _annotatable_chart(ctx, frame, "group_bracket")
    if found is None:
        return
    group, state = found
    index = _index(query)
    if index is None or not 0 <= index < len(state.annotations):
        return
    if state.annotations[index].kind != "group_bracket":
        return
    textdialog.request_edit(ctx, frame, group, state, index)


def _index(query: str) -> int | None:
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        return int(args["index"])
    except (KeyError, ValueError):
        return None


def change_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Change label or style of one annotation (``index=1&label=absolute``); one undo step."""
    _update_annotations(ctx, frame, lambda notes: annotations.changed(notes, query))


def remove_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Remove the annotation at ``index=...``; one undo step."""
    _update_annotations(ctx, frame, lambda notes: annotations.removed(notes, query))


def remove_annotations(ctx: Any, frame: Any) -> None:
    """Remove all annotations of the selected chart; one undo step."""
    _update_annotations(ctx, frame, lambda _: ())


Update = Callable[[tuple[Annotation, ...]], tuple[Annotation, ...]]


def _update_annotations(ctx: Any, frame: Any, update: Update) -> None:
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    doc = frame.getController().getModel()
    try:
        changed_state = replace(state, annotations=update(state.annotations))
    except ValueError:
        # a bad index or a state the chart kind rejects (e.g. a median mode on a Gantt date line)
        ui.show_info(ctx, frame, text("annotation_unsupported", ui.ui_locale(ctx)))
        return
    chart.redraw(doc, group, changed_state)


def same_scale(ctx: Any, frame: Any) -> None:
    """Put the selected charts (and their groups) on one shared scale; one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    groups = selected_charts(controller)
    if len(groups) < 2:
        ui.show_info(ctx, frame, text("same_scale_need_two", locale))
        return
    doc = controller.getModel()
    states = _claimed_states(ctx, frame, doc, groups, locale)
    if states is None:
        return
    if not core_samescale.can_join([state for _, state in states]):
        ui.show_info(ctx, frame, text("same_scale_incompatible", locale))
        return
    group_ids = {state.scale_group for _, state in states if state.scale_group is not None}
    if len(group_ids) == 1:
        only = next(iter(group_ids))
        if all(state.scale_group == only for _, state in states):
            return
    group_id = samescale.new_group_id()
    changes = {group: replace(state, scale_group=group_id) for group, state in states}
    for group, state in _group_members(doc, group_ids):
        changes.setdefault(group, replace(state, scale_group=group_id))
    chart.apply_changes(doc, changes)


def remove_same_scale(ctx: Any, frame: Any) -> None:
    """Give the selected charts (and their groups) their own scale again; one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    groups = selected_charts(controller)
    if not groups:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return
    doc = controller.getModel()
    states = _claimed_states(ctx, frame, doc, groups, locale)
    if states is None:
        return
    group_ids = {state.scale_group for _, state in states if state.scale_group is not None}
    if not group_ids:
        return
    changes = {
        group: replace(state, scale_group=None) for group, state in _group_members(doc, group_ids)
    }
    chart.apply_changes(doc, changes)


def copy_chart_format(ctx: Any, frame: Any) -> None:
    """Remember the selected chart's format and series colours for :func:`apply_chart_format`."""
    global _format_slot
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    states = _claimed_states(ctx, frame, controller.getModel(), selected_charts(controller), locale)
    if states is None:
        return
    if len(states) != 1:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return
    _format_slot = states[0][1]
    ui.show_info(ctx, frame, text("format_copied", locale))


def apply_chart_format(ctx: Any, frame: Any) -> None:
    """Apply the copied chart format to every selected chart; one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    if _format_slot is None:
        ui.show_info(ctx, frame, text("format_not_copied", locale))
        return
    doc = controller.getModel()
    states = _claimed_states(ctx, frame, doc, selected_charts(controller), locale)
    if states is None:
        return
    changes: dict[Any, ChartState] = {}
    for group, state in states:
        applied = formats.apply(state, _format_slot)
        if applied != state:
            changes[group] = applied
    chart.apply_changes(doc, changes)


def set_scheme(ctx: Any, frame: Any, query: str) -> None:
    """Switch the document to a built-in colour scheme (``name=Grey``); one undo step."""
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    chosen = style.built_in(args.get("name", ""))
    if chosen is None:
        ui.show_info(ctx, frame, text("scheme_unknown", locale))
        return
    chart.set_scheme(frame.getController().getModel(), chosen)


def load_scheme(ctx: Any, frame: Any) -> None:
    """Load a colour-scheme file and make it the document's scheme; one undo step."""
    locale = ui.ui_locale(ctx)
    path = _pick_file(ctx, text("scheme_title_load", locale), save=False)
    if path is None:
        return
    try:
        loaded = style.scheme_from_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, style.SchemeError) as exc:
        ui.show_info(ctx, frame, text("scheme_load_failed", locale, detail=str(exc)))
        return
    chart.set_scheme(frame.getController().getModel(), loaded)
    ui.show_info(ctx, frame, text("scheme_loaded", locale, name=loaded.name))


def save_scheme(ctx: Any, frame: Any) -> None:
    """Save the document's current colour scheme to a file."""
    locale = ui.ui_locale(ctx)
    doc = frame.getController().getModel()
    path = _pick_file(ctx, text("scheme_title_save", locale), save=True)
    if path is None:
        return
    try:
        Path(path).write_text(style.scheme_to_json(scheme.load(doc)), encoding="utf-8")
    except OSError as exc:
        ui.show_info(ctx, frame, text("scheme_save_failed", locale, detail=str(exc)))
        return
    ui.show_info(ctx, frame, text("scheme_saved", locale, path=path))


def check_design(ctx: Any, frame: Any, query: str) -> None:
    """Check the presentation against a corporate design file and offer to fix it (M19, ADR 0029).

    ``CheckDesign?file=<url>`` skips the file picker; ``fix=true`` fixes without asking (macros,
    tests) and ``fix=false`` only reports. Without ``fix`` the report asks whether to fix: one undo
    step. Without a window (headless) the report is printed.
    """
    locale = ui.ui_locale(ctx)
    doc = frame.getController().getModel()
    location = _query_arg(query, "file")
    if not location:
        location = _pick_file(ctx, text("design_title_load", locale), save=False) or ""
        if not location:
            return
    try:
        rules = designcheck.read_rules(location)
    except core_design.DesignError as exc:
        ui.tell(ctx, frame, text("design_load_failed", locale, detail=str(exc)))
        return
    fix = _query_arg(query, "fix")
    result = designcheck.inspect(doc, rules)
    if result.clean:
        ui.tell(ctx, frame, core_design.report(result, locale))
        return
    if fix == "false":
        ui.tell(ctx, frame, core_design.report(result, locale))
        return
    if fix != "true":
        question = core_design.report(result, locale) + "\n\n" + text("design_ask_fix", locale)
        if not ui.ask(ctx, frame, question):
            return
    designcheck.check_and_fix(doc, rules)
    ui.tell(ctx, frame, text("design_done", locale, count=str(len(result.findings))))


def simulate_colorblind(ctx: Any, frame: Any, query: str) -> None:
    """Replace the document's colours with their colour-blind simulation (M30); one undo step."""
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    kind = args.get("kind", "deuteranopia")
    doc = frame.getController().getModel()
    try:
        simulated = colorblind.scheme(scheme.load(doc), kind)  # pyright: ignore[reportArgumentType]
    except ValueError:
        ui.show_info(ctx, frame, text("colorblind_unknown", locale))
        return
    chart.set_scheme(doc, simulated)


def alt_text_all(ctx: Any, frame: Any) -> None:
    """Give every shape without alternative text a short description (M30)."""
    locale = ui.ui_locale(ctx)
    count = alttextall.apply(ctx, frame.getController().getModel())
    ui.tell(ctx, frame, text("alt_text_done", locale, count=str(count)))


def theme_editor(ctx: Any, frame: Any) -> None:
    """Open the palette and font dialog (M30); one undo step on OK."""
    themedialog.request(ctx, frame)


def table_options(ctx: Any, frame: Any, query: str) -> None:
    """Open the table options dialog, or apply its fields from ``query`` (M25)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if state.kind != "table":
        ui.show_info(ctx, frame, text("option_unsupported", locale))
        return
    if not query:
        tabledialog.request(ctx, frame, group, state)
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        changed = core_table.changed(state.table or TableSpec(), args)
    except ValueError:
        ui.show_info(ctx, frame, text("table_options_invalid", locale))
        return
    chart.redraw(frame.getController().getModel(), group, replace(state, table=changed))


def matrix_options(ctx: Any, frame: Any, query: str) -> None:
    """Open the matrix options dialog, or apply its fields from ``query`` (M25)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    if state.kind != "matrix":
        ui.show_info(ctx, frame, text("option_unsupported", locale))
        return
    if not query:
        matrixdialog.request(ctx, frame, group, state)
        return
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    try:
        changed = core_matrix.changed(state.matrix or MatrixSpec(), args)
    except ValueError:
        ui.show_info(ctx, frame, text("matrix_options_invalid", locale))
        return
    chart.redraw(frame.getController().getModel(), group, replace(state, matrix=changed))


def audit_deck(ctx: Any, frame: Any, query: str) -> None:
    """Report unreadable charts, links, stale sources and design deviations (M29)."""
    locale = ui.ui_locale(ctx)
    doc = frame.getController().getModel()
    findings = list(lo_audit.inspect(doc))
    location = _query_arg(query, "file")
    if location:
        try:
            rules = designcheck.read_rules(location)
        except core_design.DesignError as exc:
            ui.show_info(ctx, frame, text("design_load_failed", locale, detail=str(exc)))
            return
        result = designcheck.inspect(doc, rules)
        findings += [
            core_audit.Finding(
                (finding.slide + 1) if finding.slide is not None and finding.slide >= 0 else 0,
                "audit_design",
                f"{finding.issue}: {finding.actual} -> {finding.expected}",
            )
            for finding in result.findings
        ]
    if findings:
        auditdialog.request(ctx, frame, tuple(findings), locale)
    else:
        ui.tell(ctx, frame, core_audit.report((), locale))


def batch_format(ctx: Any, frame: Any, query: str) -> None:
    """Apply one format option to every selected chart (M29); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    states = _claimed_states(ctx, frame, controller.getModel(), selected_charts(controller), locale)
    if states is None:
        return
    changes: dict[Any, ChartState] = {}
    for group, state in states:
        try:
            fmt = formats.settled(state, state.format, query)
        except ValueError:
            ui.show_info(ctx, frame, text("option_unsupported", locale))
            return
        if fmt != state.format:
            changes[group] = replace(state, format=fmt)
    chart.apply_changes(controller.getModel(), changes)


def batch_import(ctx: Any, frame: Any, query: str) -> None:
    """Import the same table into every selected chart (M29); one undo step."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    states = _claimed_states(ctx, frame, controller.getModel(), selected_charts(controller), locale)
    if states is None:
        return
    location = _query_arg(query, "url")
    if not location:
        ui.show_info(ctx, frame, text("import_invalid", locale))
        return
    try:
        rows = dataimport.read_file(ctx, location, _query_arg(query, "sheet"))
    except (OSError, core_import.ImportError) as exc:
        ui.show_info(ctx, frame, text("import_data_failed", locale, detail=str(exc)))
        return
    changes: dict[Any, ChartState] = {}
    for group, state in states:
        try:
            changes[group] = core_import.state_with_table(state, rows)
        except core_import.ImportError:
            ui.show_info(ctx, frame, text("import_invalid", locale))
            return
    chart.apply_changes(controller.getModel(), changes)


def export_deck_spec(ctx: Any, frame: Any, query: str) -> None:
    """Write the charts of the presentation as a deck specification (M29)."""
    locale = ui.ui_locale(ctx)
    doc = frame.getController().getModel()
    entries: list[tuple[str, ChartState]] = []
    for group, chart_id in store.all_charts(doc):
        try:
            state = store.read_state(doc, chart_id)
        except (StateError, ValueError):
            continue
        if state is not None and state.kind not in ("table", "matrix"):
            entries.append((str(group.Name), state))
    location = _query_arg(query, "url") or _pick_file(
        ctx, text("menu_export_spec", locale), save=True
    )
    if not location:
        return
    try:
        path = uno.fileUrlToSystemPath(links.as_url(location))
        Path(path).write_text(deck_export.to_json(entries), encoding="utf-8")
    except Exception as exc:
        ui.show_info(ctx, frame, text("spec_export_failed", locale, detail=str(exc)))
        return
    ui.tell(ctx, frame, text("spec_exported", locale, count=str(len(entries))))


def import_data(ctx: Any, frame: Any, query: str) -> None:
    """Replace the selected chart's data sheet from a CSV, ODS or XLSX file (M28)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    group, state = found
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    location = args.get("url", "")
    if not location:
        location = _pick_import_file(ctx, text("import_data_title", locale), "data", locale) or ""
        if not location:
            return
    try:
        rows = dataimport.read_file(ctx, location, args.get("sheet", ""))
        changed = core_import.state_with_table(state, rows)
    except (OSError, core_import.ImportError) as exc:
        detail = text(exc.key, locale) if isinstance(exc, core_import.ImportError) else str(exc)
        ui.show_info(ctx, frame, text("import_data_failed", locale, detail=detail))
        return
    chart.redraw(frame.getController().getModel(), group, changed)


def insert_from_clipboard(ctx: Any, frame: Any) -> None:
    """Insert a column chart from the CSV/TSV text on the clipboard (M28); one undo step."""
    locale = ui.ui_locale(ctx)
    text_ = dataimport.clipboard_text(ctx)
    if not text_.strip():
        ui.show_info(ctx, frame, text("clipboard_empty", locale))
        return
    try:
        rows = core_import.table(text_)
        state = core_import.state_with_table(_with_default_format_for("column", locale), rows)
    except (ValueError, core_import.ImportError):
        ui.show_info(ctx, frame, text("import_invalid", locale))
        return
    controller = frame.getController()
    resize.watch(controller.getModel())
    controller.select(chart.insert_at(controller.getModel(), controller.getCurrentPage(), state))


def _with_default_format_for(kind: str, locale: str) -> ChartState:
    from librecharts.core.datasheet import sample_state
    from librecharts.core.format import default_format

    state = sample_state()
    return replace(state, kind=kind, format=default_format(kind, state.grouping, locale))


def save_template(ctx: Any, frame: Any, query: str) -> None:
    """Save the selected chart as a template in the user's template folder (M27)."""
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    _, state = found
    locale = ui.ui_locale(ctx)
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    name = args.get("name", "")
    if not name:
        name = textdialog.ask_text(ctx, frame, "template_save_title", "template_name", "") or ""
        if not name:
            return
    try:
        path = lo_templates.save(
            ctx,
            core_templates.Template(
                name, core_templates.stripped(state), args.get("description", "")
            ),
        )
    except (OSError, ValueError) as exc:
        ui.show_info(ctx, frame, text("template_save_failed", locale, detail=str(exc)))
        return
    ui.show_info(ctx, frame, text("template_saved", locale, path=str(path)))


def insert_template(ctx: Any, frame: Any, query: str) -> None:
    """Insert a template at the slide centre (M27); one undo step."""
    args = {key: values[-1] for key, values in parse_qs(query).items()}
    name = args.get("name", "")
    locale = ui.ui_locale(ctx)
    if not name:
        name = textdialog.ask_text(ctx, frame, "menu_insert_template", "template_name", "") or ""
        if not name:
            return
    path = lo_templates.find(ctx, name)
    if path is None:
        ui.show_info(ctx, frame, text("template_missing", locale, name=name))
        return
    try:
        template = lo_templates.load(path)
    except (OSError, core_templates.TemplateError) as exc:
        ui.show_info(ctx, frame, text("template_load_failed", locale, detail=str(exc)))
        return
    controller = frame.getController()
    resize.watch(controller.getModel())
    controller.select(
        chart.insert_at(controller.getModel(), controller.getCurrentPage(), template.state)
    )


def export_csv(ctx: Any, frame: Any, query: str) -> None:
    """Write the selected chart's data sheet to a CSV file (M20, ADR 0030).

    ``ExportCsv?url=<url>`` skips the file picker (macros, tests). Nothing in the presentation
    changes, so there is no undo step.
    """
    found = _annotatable_chart(ctx, frame, None)
    if found is None:
        return
    _, state = found
    locale = ui.ui_locale(ctx)
    location = _query_arg(query, "url")
    url = links.as_url(location) if location else _pick_csv_target(ctx, locale)
    if not url:
        return
    try:
        path = uno.fileUrlToSystemPath(url)
        # A byte order mark makes spreadsheets read the file as UTF-8.
        Path(path).write_text(csvexport.to_csv(state), encoding="utf-8-sig", newline="")
    except Exception as exc:  # not a file URL, folder missing, not writable
        ui.tell(ctx, frame, text("csv_export_failed", locale, detail=str(exc)))
        return
    if not location:
        ui.tell(ctx, frame, text("csv_exported", locale, path=path))


def _pick_csv_target(ctx: Any, locale: str) -> str | None:
    picker = ctx.ServiceManager.createInstanceWithContext("com.sun.star.ui.dialogs.FilePicker", ctx)
    picker.initialize((10,))  # TemplateDescription.FILESAVE_AUTOEXTENSION
    picker.setTitle(text("csv_title_save", locale))
    label = text("csv_filter", locale)
    picker.appendFilter(label, "*.csv")
    picker.setCurrentFilter(label)
    picker.setDefaultName(csvexport.DEFAULT_NAME)
    if picker.execute() != 1:  # com.sun.star.ui.dialogs.ExecutableDialogResults.OK
        return None
    files = picker.getFiles()
    return str(files[0]) if files else None


def _pick_file(ctx: Any, title: str, *, save: bool) -> str | None:
    """Ask for a scheme file with LibreOffice's file picker; ``None`` if the user cancels."""
    picker = ctx.ServiceManager.createInstanceWithContext("com.sun.star.ui.dialogs.FilePicker", ctx)
    picker.setTitle(title)
    label = text("scheme_filter", ui.ui_locale(ctx))
    picker.appendFilter(label, "*.json")
    picker.setCurrentFilter(label)
    if save:
        picker.setDefaultName("librecharts-scheme.json")
    if picker.execute() != 1:  # com.sun.star.ui.dialogs.ExecutableDialogResults.OK
        return None
    files = picker.getFiles()
    return str(files[0]) if files else None


def _claimed_states(
    ctx: Any, frame: Any, doc: Any, groups: list[Any], locale: str
) -> list[tuple[Any, ChartState]] | None:
    """The state of every chart group, claiming renamed copies.

    Shows a message and returns ``None`` if a chart is orphaned or its state is corrupt.
    """
    found: list[tuple[Any, ChartState]] = []
    for group in groups:
        chart_id = store.claim(doc, group)
        try:
            state = store.read_state(doc, chart_id) if chart_id else None
        except StateError as exc:
            ui.show_info(ctx, frame, text("corrupt_chart", locale, detail=str(exc)))
            return None
        if state is None:
            ui.show_info(ctx, frame, text("orphaned_chart", locale))
            return None
        found.append((group, state))
    return found


def _group_members(doc: Any, group_ids: set[str]) -> list[tuple[Any, ChartState]]:
    """Every named chart in one of the scale groups, with its stored state."""
    members: list[tuple[Any, ChartState]] = []
    if not group_ids:
        return members
    for group, chart_id in store.all_charts(doc):
        try:
            state = store.read_state(doc, chart_id)
        except StateError:
            continue
        if state is not None and state.scale_group in group_ids:
            members.append((group, state))
    return members


def _annotatable_chart(
    ctx: Any, frame: Any, kind: AnnotationKind | None
) -> tuple[Any, ChartState] | None:
    """The selected chart and its state if it can get an annotation of ``kind`` (any chart for
    ``None``); else tell the user why not and return ``None``."""
    controller = frame.getController()
    locale = ui.ui_locale(ctx)
    group = selected_chart(controller)
    if group is None:
        ui.show_info(ctx, frame, text("select_chart", locale))
        return None
    doc = controller.getModel()
    chart_id = store.claim(doc, group)
    try:
        state = store.read_state(doc, chart_id) if chart_id else None
    except StateError as exc:
        ui.show_info(ctx, frame, text("corrupt_chart", locale, detail=str(exc)))
        return None
    if state is None:
        ui.show_info(ctx, frame, text("orphaned_chart", locale))
        return None
    if kind is not None and not supports(state, kind):
        ui.show_info(ctx, frame, text("annotation_unsupported", locale))
        return None
    return group, state


def selected_charts(controller: Any) -> list[Any]:
    """Every selected LibreCharts group, including charts inside a multiple selection."""
    return _charts_in(controller.getSelection())


def _charts_in(selection: Any) -> list[Any]:
    if selection is None:
        return []
    if _is_chart(selection):
        return [selection]
    if hasattr(selection, "getCount"):
        found: list[Any] = []
        for index in range(selection.getCount()):
            found.extend(_charts_in(selection.getByIndex(index)))
        return found
    return []


def selected_chart(controller: Any) -> Any:
    """The selected LibreCharts group, or ``None`` unless exactly one chart is selected."""
    selection = controller.getSelection()
    if selection is None:
        return None
    # Check the selection itself first: a group shape also has getCount() (its children).
    if _is_chart(selection):
        return selection
    if hasattr(selection, "getCount") and selection.getCount() == 1:
        candidate = selection.getByIndex(0)
        if _is_chart(candidate):
            return candidate
    return None


def _is_chart(shape: Any) -> bool:
    try:
        return store.chart_id_of(shape) is not None
    except AttributeError:  # e.g. a shape collection has no Name
        return False
