"""Pick mode: the user clicks the columns an annotation connects (M4 plan, "Interaction").

The adapter feeds :class:`PickSession` with the chart-relative centre of every shape the user
selects inside the chart; the session turns them into columns and, after the last one, into an
annotation. Everything here is plain data, so the flow is tested without LibreOffice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast, get_args
from urllib.parse import parse_qs

from librecharts.core import annotations as notes
from librecharts.core import sorting
from librecharts.core.datasheet import parse
from librecharts.core.layout.bar import bar_at
from librecharts.core.layout.column import column_at
from librecharts.core.layout.waterfall import step_at
from librecharts.core.model import Annotation, AnnotationKind, ArrowStyle, ChartState
from librecharts.core.waterfall import parse_waterfall

Target = tuple[int, int | None]  # category, series (None: the column as a whole)


def target_at(state: ChartState, width: float, height: float, x: float, y: float) -> Target | None:
    """The column (or bar) at chart point (x, y), or ``None`` if there is none to annotate.

    The returned category is the data sheet index, even when sorting drew the category elsewhere.
    """
    if state.kind == "column":
        data = parse(state)
        order = sorting.order(data, state.grouping, state.sort)
        data = sorting.sorted_data(data, order)
        annotations = sorting.remap(state.annotations, order)
        target = column_at(data, state.grouping, width, annotations, x, y, state.format)
        return _to_data_index(target, order)
    if state.kind == "bar":
        data = parse(state)
        order = sorting.order(data, state.grouping, state.sort)
        data = sorting.sorted_data(data, order)
        annotations = sorting.remap(state.annotations, order)
        target = bar_at(data, state.grouping, width, height, annotations, x, y, state.format)
        return _to_data_index(target, order)
    if state.kind == "waterfall":
        return step_at(parse_waterfall(state), width, state.annotations, x, y, state.format)
    return None


def _to_data_index(target: Target | None, order: tuple[int, ...]) -> Target | None:
    if target is None:
        return None
    category, series = target
    return order[category], series


@dataclass
class PickSession:
    """Collects the picks for one annotation of ``kind``."""

    kind: Literal["difference", "cagr"]
    style: ArrowStyle = "bracket"
    picks: list[Target] = field(default_factory=list[Target])

    @classmethod
    def from_query(cls, query: str) -> PickSession:
        """Parse command arguments like ``kind=difference&style=level``.

        Raises ``ValueError`` for a missing or unknown kind or style.
        """
        args = {key: values[-1] for key, values in parse_qs(query).items()}
        kind, style = args.get("kind"), args.get("style", "bracket")
        if kind not in ("difference", "cagr"):  # an axis break needs no picks
            raise ValueError(f"unknown annotation kind: {kind!r}")
        if style not in get_args(ArrowStyle):
            raise ValueError(f"unknown arrow style: {style!r}")
        return cls(kind, cast("ArrowStyle", style))

    @property
    def prompt(self) -> str:
        """Message key telling the user what to click next."""
        return "pick_end" if self.picks else "pick_start"

    def add(self, target: Target) -> Annotation | None:
        """Record a pick; the finished annotation once enough columns are picked.

        Picking the start column again is ignored, so a second click on it changes nothing.
        """
        if self.picks and target[0] == self.picks[0][0]:
            return None
        self.picks.append(target)
        if len(self.picks) < 2:
            return None
        (start, start_series), (end, end_series) = self.picks
        # Both ends must measure the same thing: one series' bars, or else the column totals.
        series = start_series if start_series == end_series else None
        return Annotation(self.kind, start, end, series, self.style)


def supports(state: ChartState, kind: AnnotationKind) -> bool:
    if state.percent:  # a 100 % chart has no annotations: they stay stored but are not offered
        return False
    return kind in notes.SUPPORTED.get(state.kind, frozenset())
