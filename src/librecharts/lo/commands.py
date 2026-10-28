"""Menu commands, called by extension/entry.py with the frame the command was invoked in."""

from __future__ import annotations

from typing import Any

from librecharts.core import annotations
from librecharts.core.messages import text
from librecharts.core.model import AnnotationKind, ChartState
from librecharts.core.picking import PickSession, supports
from librecharts.core.state_io import StateError
from librecharts.lo import chart, pick, resize, store, ui
from librecharts.lo.datasheet import OrphanedChartError, open_datasheet


def insert_column_chart(frame: Any) -> None:
    _insert(frame, chart.insert_column_chart)


def insert_bar_chart(frame: Any) -> None:
    _insert(frame, chart.insert_bar_chart)


def insert_waterfall_chart(frame: Any) -> None:
    _insert(frame, chart.insert_waterfall_chart)


def insert_mekko_chart(frame: Any) -> None:
    _insert(frame, chart.insert_mekko_chart)


def _insert(frame: Any, insert: Any) -> None:
    controller = frame.getController()
    doc = controller.getModel()
    group = insert(doc, controller.getCurrentPage())
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
        open_datasheet(
            desktop, controller.getModel(), group, text("datasheet_title", locale), load_args
        )
    except OrphanedChartError:
        ui.show_info(ctx, frame, text("orphaned_chart", locale))
    except StateError as exc:
        ui.show_info(ctx, frame, text("corrupt_chart", locale, detail=str(exc)))


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


def _annotatable_chart(ctx: Any, frame: Any, kind: AnnotationKind) -> tuple[Any, ChartState] | None:
    """The selected chart and its state if it can get an annotation of ``kind``; else tell the
    user why not and return ``None``."""
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
    if not supports(state, kind):
        ui.show_info(ctx, frame, text("annotation_unsupported", locale))
        return None
    return group, state


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
