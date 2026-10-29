"""Menu commands, called by extension/entry.py with the frame the command was invoked in."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from librecharts.core import annotations, gantt, options, style
from librecharts.core import format as formats
from librecharts.core import links as core_links
from librecharts.core import samescale as core_samescale
from librecharts.core.messages import text
from librecharts.core.model import Annotation, AnnotationKind, ChartState
from librecharts.core.picking import PickSession, supports
from librecharts.core.state_io import StateError
from librecharts.lo import (
    axisdialog,
    chart,
    datasheet,
    formatdialog,
    linkdialog,
    links,
    pick,
    resize,
    samescale,
    scheme,
    store,
    ui,
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


def _insert(ctx: Any, frame: Any, insert: Any) -> None:
    controller = frame.getController()
    doc = controller.getModel()
    group = insert(doc, controller.getCurrentPage(), locale=ui.ui_locale(ctx))
    resize.watch(
        doc
    )  # normally done by the document-open job; covers a freshly installed extension
    controller.select(group)


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
        linked = links.link(ctx, doc, state, links.as_url(args.get("url", "")), *checked)
    except links.LinkError as exc:
        ui.show_info(ctx, frame, exc.message(locale))
        return
    chart.redraw(doc, group, linked)
    _refresh_datasheet(doc, group)


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
    _update_links(ctx, frame, doc, links.targets(doc, ids), single=len(ids) == 1)


def update_all_links(ctx: Any, frame: Any) -> None:
    """Update every linked chart of the presentation; one undo step, each source opened once."""
    doc = frame.getController().getModel()
    links.withdraw_offer(doc)
    _update_links(ctx, frame, doc, links.targets(doc), single=False)


def _update_links(ctx: Any, frame: Any, doc: Any, targets: list[Any], *, single: bool) -> None:
    outcome = links.update(ctx, doc, targets)
    chart.apply_changes(doc, dict(outcome.changed.values()))
    # Same data: only the link's times are new. Not worth an undo step; nothing is redrawn.
    for chart_id, state in outcome.unchanged.items():
        store.write_state(doc, chart_id, state)
    for chart_id in (*outcome.changed, *outcome.unchanged):
        datasheet.refresh(doc, chart_id)
    count = len(outcome.changed) + len(outcome.unchanged)
    locale = ui.ui_locale(ctx)
    message = core_links.report(
        count, len(outcome.changed), outcome.problems, locale, single=single
    )
    if message:
        ui.show_info(ctx, frame, message)


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


def add_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Add the annotation described by ``query`` (see ``annotations.from_query``) to the selected
    chart; one undo step. Used by tests and scripts; users pick columns instead."""
    annotation = annotations.from_query(query)
    found = _annotatable_chart(ctx, frame, annotation.kind)
    if found is not None:
        group, _ = found
        chart.add_annotation(frame.getController().getModel(), group, annotation)


def pick_annotation(ctx: Any, frame: Any, query: str) -> None:
    """Start pick mode for the annotation kind (and style) in ``query`` on the selected chart."""
    session = PickSession.from_query(query)
    found = _annotatable_chart(ctx, frame, session.kind)
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


def number_format(ctx: Any, frame: Any) -> None:
    """Ask for the number format of the selected chart (a dialog), then apply it."""
    found = _annotatable_chart(ctx, frame, None)
    if found is not None:
        group, state = found
        formatdialog.request_number(ctx, frame, group, state)


def value_line(ctx: Any, frame: Any) -> None:
    """Ask for a value line (a target or the average) and add it; one undo step."""
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
    if found is not None:
        group, state = found
        doc = frame.getController().getModel()
        chart.redraw(doc, group, replace(state, annotations=update(state.annotations)))


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
