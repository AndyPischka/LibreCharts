"""Chart operations on a presentation: insert and redraw. Entry points for extension/entry.py.

Every operation is exactly one entry in the document's undo list (see lo/undo.py).
"""

from __future__ import annotations

from typing import Any

from librecharts.core.datasheet import parse, sample_state
from librecharts.core.layout.column import layout_column
from librecharts.core.model import ChartState
from librecharts.lo import render, store, undo

NEW_CHART_SHARE = 0.6  # a new chart covers this share of the slide's width and height


def insert_column_chart(doc: Any, page: Any, state: ChartState | None = None) -> Any:
    """Insert a chart (sample data by default) centred on ``page``; returns its group shape."""
    state = state or sample_state()
    width = round(page.Width * NEW_CHART_SHARE)
    height = round(page.Height * NEW_CHART_SHARE)
    x, y = (page.Width - width) // 2, (page.Height - height) // 2
    primitives = layout_column(parse(state), state.grouping, width, height)

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


def _apply(doc: Any, group: Any, chart_id: str, state: ChartState) -> None:
    size = group.Size
    primitives = layout_column(parse(state), state.grouping, size.Width, size.Height)
    with undo.recording_locked(doc):
        render.rerender(doc, group, primitives)
    store.write_state(doc, chart_id, state)
