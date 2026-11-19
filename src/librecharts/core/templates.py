"""Chart templates: a named chart state in a small JSON file (M27).

A template stores everything that makes a chart a starting point: kind, options, format, colours,
annotations, label overrides and sample data. A data link and a same-scale group belong to the
document, not to the look, so :func:`stripped` removes them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any, cast

from librecharts.core.model import ChartState
from librecharts.core.state_io import StateError
from librecharts.core.state_io import from_json as state_from_json
from librecharts.core.state_io import to_json as state_to_json

VERSION = 1
FORBIDDEN = '<>:"/\\|?*'


@dataclass(frozen=True, slots=True)
class Template:
    name: str
    state: ChartState
    description: str = ""

    def __post_init__(self) -> None:
        if not 1 <= len(self.name) <= 80:
            raise ValueError("a template name must be 1 to 80 characters")
        if len(self.description) > 200:
            raise ValueError("a template description must be at most 200 characters")


class TemplateError(ValueError):
    """A template file is malformed or from a newer LibreCharts."""


def stripped(state: ChartState) -> ChartState:
    """The state without the data link and the same-scale group."""
    return replace(state, link=None, scale_group=None)


def to_json(template: Template) -> str:
    return json.dumps(
        {
            "version": VERSION,
            "name": template.name,
            "description": template.description,
            "state": json.loads(state_to_json(template.state)),
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def from_json(text: str) -> Template:
    try:
        raw = json.loads(text)
    except ValueError as exc:
        raise TemplateError(f"invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise TemplateError("a template must be a JSON object")
    data = cast("dict[str, Any]", raw)
    version = data.get("version")
    if version != VERSION:
        raise TemplateError(f"unsupported template version: {version!r}")
    name, description, state = data.get("name"), data.get("description", ""), data.get("state")
    if not isinstance(name, str) or not isinstance(description, str) or not isinstance(state, dict):
        raise TemplateError("a template needs a name, a description and a chart state")
    try:
        chart = state_from_json(json.dumps(state))
    except StateError as exc:
        raise TemplateError(str(exc)) from exc
    return Template(name, chart, description)


def file_name(name: str) -> str:
    """A safe ``.json`` file name from a template name."""
    cleaned = re.sub(f"[{re.escape(FORBIDDEN)}]", "-", name).strip(" .-")
    cleaned = re.sub(r"\s+", "-", cleaned)
    if not cleaned:
        cleaned = "chart"
    return f"{cleaned[:80]}.json"
