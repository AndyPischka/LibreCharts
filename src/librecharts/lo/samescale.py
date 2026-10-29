# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Same-scale groups in a presentation: redraw all charts a change touches (ADR 0017).

The group id lives in ``ChartState.scale_group``; the shared length per value unit is never stored
but recomputed from the charts' current sizes, so it stays right after a resize, an undo or a
reload. One layout change can affect several charts; :func:`apply_states` redraws the updated
charts and every chart of the groups involved inside one undo lock.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from librecharts.core import samescale
from librecharts.core.layout.chart import layout_chart
from librecharts.core.model import ChartState
from librecharts.core.state_io import StateError
from librecharts.lo import render, scheme, store, undo


class SameScaleError(ValueError):
    """The selected charts cannot share one scale."""


def new_group_id() -> str:
    """A fresh id for a new same-scale group."""
    return secrets.token_hex(6)


@dataclass(slots=True)
class _Chart:
    group: Any
    state: ChartState
    previous: ChartState | None
    width: float
    height: float


def apply_states(doc: Any, updates: dict[str, ChartState]) -> None:
    """Store and redraw ``updates`` and every chart in the scale groups involved.

    A chart that leaves a group also redraws that group's remaining charts, so they return to
    their own scale. The caller adds the undo action.
    """
    if not updates:
        return
    charts = _snapshot(doc, updates)
    group_ids = {
        group
        for chart_id in updates
        if (chart := charts.get(chart_id)) is not None
        for state in (chart.state, chart.previous)
        if state is not None and (group := state.scale_group) is not None
    }
    lengths: dict[str, float | None] = {
        group: samescale.common_length_per_unit(
            [
                (chart.state, chart.width, chart.height)
                for chart in charts.values()
                if chart.state.scale_group == group
            ]
        )
        for group in group_ids
    }
    affected = set(updates) & set(charts)
    affected |= {
        chart_id for chart_id, chart in charts.items() if chart.state.scale_group in group_ids
    }
    # Store first, then draw: the resize watcher reacts to the shapes changing below and lays
    # charts out from their stored states. A command dispatched over the UNO bridge (scripts,
    # tests) runs beside it, and stale states made it move a redrawn peer back to the old scale.
    for chart_id in sorted(affected):
        store.write_state(doc, chart_id, charts[chart_id].state)
    with undo.recording_locked(doc):
        for chart_id in sorted(affected):
            chart = charts[chart_id]
            group = chart.state.scale_group
            length = None if group is None else lengths.get(group)
            try:
                primitives = layout_chart(
                    chart.state,
                    chart.width,
                    chart.height,
                    length,
                )
            except ValueError:
                continue
            render.rerender(doc, chart.group, primitives, scheme.look(doc, chart.state))


def group_length_per_unit(doc: Any, chart_id: str, state: ChartState) -> float | None:
    """The shared length per value unit of ``state``'s group, or ``None`` for its own scale."""
    if state.scale_group is None:
        return None
    charts: list[samescale.ChartSize] = []
    for group, other_id in store.all_charts(doc):
        if other_id != chart_id:
            try:
                other = store.read_state(doc, other_id)
            except StateError:
                continue
            if other is None or other.scale_group != state.scale_group:
                continue
            size = group.Size
            charts.append((other, float(size.Width), float(size.Height)))
        else:
            size = group.Size
            charts.append((state, float(size.Width), float(size.Height)))
    return samescale.common_length_per_unit(charts)


def peers(doc: Any, chart_id: str, state: ChartState) -> list[tuple[Any, ChartState]]:
    """The other charts of ``state``'s same-scale group, with their shapes and states."""
    if state.scale_group is None:
        return []
    found: list[tuple[Any, ChartState]] = []
    for group, other_id in store.all_charts(doc):
        if other_id == chart_id:
            continue
        try:
            other = store.read_state(doc, other_id)
        except StateError:
            continue
        if other is not None and other.scale_group == state.scale_group:
            found.append((group, other))
    return found


def _snapshot(doc: Any, updates: dict[str, ChartState]) -> dict[str, _Chart]:
    """Every chart of the document with its effective state, size and previously stored state."""
    charts: dict[str, _Chart] = {}
    for group, chart_id in store.all_charts(doc):
        try:
            previous = store.read_state(doc, chart_id)
        except StateError:
            continue
        state = updates.get(chart_id, previous)
        if state is None:
            continue
        size = group.Size
        charts[chart_id] = _Chart(
            group=group,
            state=state,
            previous=previous,
            width=float(size.Width),
            height=float(size.Height),
        )
    return charts
