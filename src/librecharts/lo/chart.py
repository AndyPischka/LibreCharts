"""Chart operations on a presentation: insert and redraw. Entry points for extension/entry.py.

Every operation is exactly one entry in the document's undo list (see lo/undo.py).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from librecharts.core import annotations
from librecharts.core.datasheet import (
    sample_area_state,
    sample_line_state,
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
)
from librecharts.core.format import default_format
from librecharts.core.layout.chart import layout_chart
from librecharts.core.model import Annotation, ChartState
from librecharts.lo import render, store, undo

NEW_CHART_SHARE = 0.6  # a new chart covers this share of the slide's width and height


def insert_column_chart(
    doc: Any, page: Any, state: ChartState | None = None, locale: str = ""
) -> Any:
    """Insert a chart (sample data by default) centred on ``page``; returns its group shape.

    ``locale`` (e.g. ``de-DE``) sets the decimal separator and the language of magnitude suffixes.
    """
    return _insert(doc, page, state or sample_state(), locale)


def insert_bar_chart(doc: Any, page: Any, locale: str = "") -> Any:
    """Insert a horizontal bar chart with sample data centred on ``page``."""
    return _insert(doc, page, replace(sample_state(), kind="bar"), locale)


def insert_line_chart(doc: Any, page: Any, locale: str = "") -> Any:
    """Insert a line chart with sample data centred on ``page``."""
    return _insert(doc, page, sample_line_state(), locale)


def insert_area_chart(doc: Any, page: Any, locale: str = "") -> Any:
    """Insert a stacked area chart with sample data centred on ``page``."""
    return _insert(doc, page, sample_area_state(), locale)


def insert_waterfall_chart(doc: Any, page: Any, locale: str = "") -> Any:
    """Insert a waterfall chart with sample data centred on ``page``."""
    return _insert(doc, page, sample_waterfall_state(), locale)


def insert_mekko_chart(doc: Any, page: Any, locale: str = "") -> Any:
    """Insert a percent Marimekko chart with sample data centred on ``page``."""
    return _insert(doc, page, sample_mekko_state(), locale)


def _insert(doc: Any, page: Any, state: ChartState, locale: str = "") -> Any:
    state = replace(state, format=default_format(state.kind, state.grouping, locale))
    width = round(page.Width * NEW_CHART_SHARE)
    height = round(page.Height * NEW_CHART_SHARE)
    x, y = (page.Width - width) // 2, (page.Height - height) // 2
    primitives = layout_chart(state, width, height)

    with undo.recording_locked(doc):
        group = render.render_group(doc, page, primitives, x, y, width, height)
        chart_id = store.new_chart_id()
        group.Name = store.anchor_name(chart_id)
    # The state stays in the document after an undo; unused states are cleaned up separately.
    store.write_state(doc, chart_id, state)
    undo.add_action(
        doc,
        "Insert LibreCharts chart",
        undo=lambda: page.remove(group),
        redo=lambda: page.add(group),
    )
    return group


def redraw(doc: Any, group: Any, state: ChartState) -> None:
    """Store ``state`` for the chart in ``group`` and redraw it at the group's current size."""
    chart_id = store.chart_id_of(group)
    if chart_id is None:
        raise ValueError("shape is not a LibreCharts chart")
    previous = store.read_state(doc, chart_id)

    _apply(doc, group, chart_id, state)
    if previous is not None:
        undo.add_action(
            doc,
            "Update LibreCharts chart",
            undo=lambda: _apply(doc, group, chart_id, previous),
            redo=lambda: _apply(doc, group, chart_id, state),
        )


def add_annotation(doc: Any, group: Any, annotation: Annotation) -> None:
    """Add ``annotation`` to the chart in ``group`` and redraw it: one undo step.

    A new axis break replaces the chart's old one.
    """
    chart_id = store.chart_id_of(group)
    state = store.read_state(doc, chart_id) if chart_id else None
    if state is None:
        raise ValueError("chart has no stored state")
    redraw(doc, group, replace(state, annotations=annotations.added(state.annotations, annotation)))


def _apply(doc: Any, group: Any, chart_id: str, state: ChartState) -> None:
    size = group.Size
    primitives = layout_chart(state, size.Width, size.Height)
    with undo.recording_locked(doc):
        render.rerender(doc, group, primitives)
    store.write_state(doc, chart_id, state)


def fit_to_size(doc: Any, group: Any) -> bool:
    """Re-lay out the chart in ``group`` for the group's current size; ``True`` if anything moved.

    Used after the user resized the group. Shapes are moved in place and no undo action is added:
    LibreOffice's own undo of the resize restores them. Charts without readable state are left
    as they are, and so are groups shrunk below the minimum layout size.
    """
    chart_id = store.resolve(doc, group)
    if chart_id is None:
        return False
    try:
        state = store.read_state(doc, chart_id)
        if state is None:
            return False
        size = group.Size
        primitives = layout_chart(state, size.Width, size.Height)
    except ValueError:  # StateError, or the group is too small to lay out
        return False
    # No undo lock needed: LibreOffice does not record geometry changes made through the API.
    # "mismatch" means the children are being replaced right now (e.g. a redraw in progress);
    # leave them alone, the layout structure itself does not depend on the size.
    return render.sync_geometry(group, primitives) == "updated"
