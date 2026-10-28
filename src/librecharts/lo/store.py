"""Where chart state lives in a document (ADR 0004).

The chart's group shape is named ``librecharts:<chart-id>``; the state is JSON in the document's
custom property of the same name. Only this combination survives saving as ODP and PPTX.
No ``uno`` import here: everything goes through methods of the passed-in UNO objects.
"""

from __future__ import annotations

import uuid
from typing import Any

from librecharts.core.model import ChartState
from librecharts.core.state_io import from_json, to_json

PREFIX = "librecharts:"
_REMOVEABLE = 128  # com.sun.star.beans.PropertyAttribute.REMOVEABLE


def new_chart_id() -> str:
    return uuid.uuid4().hex[:12]


def anchor_name(chart_id: str) -> str:
    return PREFIX + chart_id


def chart_id_of(shape: Any) -> str | None:
    """The chart id if ``shape`` is a LibreCharts group, else ``None``."""
    name = str(shape.Name)
    if name.startswith(PREFIX) and len(name) > len(PREFIX):
        return name[len(PREFIX) :]
    return None


def find_charts(page: Any) -> list[tuple[Any, str]]:
    """All LibreCharts groups on ``page`` with their chart ids, in z-order."""
    found: list[tuple[Any, str]] = []
    for i in range(page.getCount()):
        shape = page.getByIndex(i)
        chart_id = chart_id_of(shape)
        if chart_id is not None:
            found.append((shape, chart_id))
    return found


def write_state(doc: Any, chart_id: str, state: ChartState) -> None:
    props = doc.getDocumentProperties().getUserDefinedProperties()
    key, text = anchor_name(chart_id), to_json(state)
    if props.getPropertySetInfo().hasPropertyByName(key):
        props.setPropertyValue(key, text)
    else:
        props.addProperty(key, _REMOVEABLE, text)


def read_state(doc: Any, chart_id: str) -> ChartState | None:
    """The stored state, or ``None`` if the document has none (e.g. chart copied from elsewhere).

    Raises ``StateError`` if the stored state is corrupt or from a newer LibreCharts.
    """
    props = doc.getDocumentProperties().getUserDefinedProperties()
    key = anchor_name(chart_id)
    if not props.getPropertySetInfo().hasPropertyByName(key):
        return None
    return from_json(str(props.getPropertyValue(key)))
