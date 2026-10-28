"""Where chart state lives in a document (ADR 0004).

The chart's group shape is named ``librecharts:<chart-id>``; the state is JSON in the document's
custom property of the same name. Only this combination survives saving as ODP and PPTX.

Copies: LibreOffice renames pasted or duplicated shapes by cutting the *trailing digits* off the
name and appending " 1", " 2", ... (``...f234`` -> ``...f 1``, ``...ae2f`` -> ``...ae2f 1``). A copy
therefore points at no stored state. New ids end in a letter so that the whole id survives in the
copy's name; ``claim`` finds the origin from it (for older ids: from a unique prefix) and gives
the copy its own id and state, so copies are edited independently.
No ``uno`` import here: everything goes through methods of the passed-in UNO objects.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from librecharts.core.model import ChartState
from librecharts.core.state_io import from_json, to_json

PREFIX = "librecharts:"
_REMOVEABLE = 128  # com.sun.star.beans.PropertyAttribute.REMOVEABLE
MIN_PREFIX = 8  # shortest name prefix trusted to identify the origin of a renamed copy


def new_chart_id() -> str:
    """12 hex characters, ending in a letter (see the module docstring on renamed copies)."""
    return uuid.uuid4().hex[:11] + secrets.choice("abcdef")


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


def all_charts(doc: Any) -> list[tuple[Any, str]]:
    """All LibreCharts groups on all slides of ``doc`` with the ids from their names."""
    pages = doc.getDrawPages()
    found: list[tuple[Any, str]] = []
    for i in range(pages.getCount()):
        found.extend(find_charts(pages.getByIndex(i)))
    return found


def resolve(doc: Any, group: Any) -> str | None:
    """The id of the stored state ``group`` displays (its own, or its origin's for an unclaimed
    copy), without changing anything; ``None`` if orphaned or not a chart."""
    name_id = chart_id_of(group)
    return None if name_id is None else _origin_id(doc, name_id)


def claim(doc: Any, group: Any) -> str | None:
    """Make ``group`` the sole owner of a stored state and return its chart id.

    Returns ``None`` if the document holds no state for it (an orphaned chart, e.g. copied in from
    another presentation). A group that is a renamed copy, or shares its name with another group,
    gets a new id and its own copy of the state.
    """
    name_id = chart_id_of(group)
    if name_id is None:
        return None
    origin = _origin_id(doc, name_id)
    if origin is None:
        return None
    shared = any(other != group and other.Name == group.Name for other, _ in all_charts(doc))
    if name_id == origin and not shared:
        return origin
    new_id = new_chart_id()
    _copy_state(doc, origin, new_id)
    group.Name = anchor_name(new_id)
    return new_id


def _stored_ids(doc: Any) -> list[str]:
    props = doc.getDocumentProperties().getUserDefinedProperties()
    names = [p.Name for p in props.getPropertySetInfo().getProperties()]
    return [n[len(PREFIX) :] for n in names if n.startswith(PREFIX)]


def _origin_id(doc: Any, name_id: str) -> str | None:
    ids = _stored_ids(doc)
    if name_id in ids:
        return name_id
    if " " not in name_id:
        return None
    base = name_id.split(" ")[0]
    if base in ids:
        return base
    matches = [i for i in ids if i.startswith(base)] if len(base) >= MIN_PREFIX else []
    return matches[0] if len(matches) == 1 else None


def _copy_state(doc: Any, source: str, target: str) -> None:
    props = doc.getDocumentProperties().getUserDefinedProperties()
    props.addProperty(anchor_name(target), _REMOVEABLE, props.getPropertyValue(anchor_name(source)))
