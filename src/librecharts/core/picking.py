"""Pick mode: the user clicks the chart points an annotation connects (M4 plan, "Interaction").

The adapter feeds :class:`PickSession` with the chart-relative centre of every shape the user
selects inside the chart; the session turns them into targets (a column, bar, line point, Mekko
segment, pie segment or scatter point) and, after the last one, into an annotation. Everything
here is plain data, so the flow is tested without LibreOffice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, cast, get_args
from urllib.parse import parse_qs

from librecharts.core import annotations as notes
from librecharts.core import sorting
from librecharts.core.datasheet import parse
from librecharts.core.layout.bar import bar_at
from librecharts.core.layout.column import column_at
from librecharts.core.layout.line import line_at
from librecharts.core.layout.mekko import mekko_at
from librecharts.core.layout.pie import pie_at
from librecharts.core.layout.scatter import scatter_at
from librecharts.core.layout.waterfall import step_at
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation, AnnotationKind, ArrowStyle, ChartState
from librecharts.core.scatter import parse_scatter
from librecharts.core.waterfall import parse_waterfall

Target = tuple[int, int | None]  # category, series (None: the column as a whole)


def target_at(state: ChartState, width: float, height: float, x: float, y: float) -> Target | None:
    """The column (or bar, line point, Mekko or pie segment, scatter point) at chart point (x, y),
    or ``None`` if there is none.

    The returned category is the data sheet index, even when sorting drew the category elsewhere.
    """
    if state.kind == "column":
        data = parse(state)
        order = sorting.order(data, state.grouping, state.sort)
        data = sorting.sorted_data(data, order)
        annotations = sorting.remap(state.annotations, order)
        target = column_at(
            data,
            state.grouping,
            width,
            annotations,
            x,
            y,
            state.format,
            height=height,
            lines=state.lines,
            secondary=state.secondary,
        )
        return _to_data_index(target, order)
    if state.kind == "bar":
        data = parse(state)
        order = sorting.order(data, state.grouping, state.sort)
        data = sorting.sorted_data(data, order)
        annotations = sorting.remap(state.annotations, order)
        target = bar_at(data, state.grouping, width, height, annotations, x, y, state.format)
        return _to_data_index(target, order)
    if state.kind == "line":
        return line_at(parse(state), width, height, state.annotations, x, y, state.format)
    if state.kind == "waterfall":
        return step_at(parse_waterfall(state), width, state.annotations, x, y, state.format)
    if state.kind == "mekko":
        return mekko_at(
            parse_mekko(state), width, height, state.percent, x, y, state.annotations, state.format
        )
    if state.kind == "pie":
        return pie_at(
            parse(state), state.doughnut, width, height, x, y, state.annotations, state.format
        )
    if state.kind == "scatter":
        return scatter_at(
            parse_scatter(state), width, height, x, y, state.annotations, state.format
        )
    return None


def _to_data_index(target: Target | None, order: tuple[int, ...]) -> Target | None:
    if target is None:
        return None
    category, series = target
    return order[category], series


@dataclass
class PickSession:
    """Collects the picks for one annotation of ``kind``.

    A category gap needs two adjacent categories, a group bracket a range of categories; neither
    looks at the series of a pick. An arrow measures a (category, series?) pair at each end: the
    same series twice (``series_end is None``) or, on a chart with several series side by side, two
    different series (of one category or of two). A CAGR always connects two different
    categories, so it never measures between series.
    """

    kind: Literal["difference", "cagr", "gap", "bracket"]
    style: ArrowStyle = "bracket"
    picks: list[Target] = field(default_factory=list[Target])

    @classmethod
    def from_query(cls, query: str) -> PickSession:
        """Parse command arguments like ``kind=difference&style=level``.

        Raises ``ValueError`` for a missing or unknown kind or style.
        """
        args = {key: values[-1] for key, values in parse_qs(query).items()}
        kind, style = args.get("kind"), args.get("style", "bracket")
        if kind not in ("difference", "cagr", "gap", "bracket"):  # axis breaks need no picks
            raise ValueError(f"unknown annotation kind: {kind!r}")
        if style not in get_args(ArrowStyle):
            raise ValueError(f"unknown arrow style: {style!r}")
        return cls(kind, cast("ArrowStyle", style))

    @property
    def prompt(self) -> str:
        """Message key telling the user what to click next."""
        if self.kind in ("gap", "bracket"):
            return f"pick_{self.kind}_{'end' if self.picks else 'start'}"
        return "pick_end" if self.picks else "pick_start"

    def add(self, target: Target) -> Annotation | None:
        """Record a pick; the finished annotation once enough columns are picked.

        Picking the first target again is ignored, so a second click on it changes nothing; a CAGR
        needs two different categories (it measures growth over time, not between series). The
        second category of a gap must be adjacent to the first, a bracket's end may be any
        category; both ends keep their order.
        """
        if self.picks and (
            target == self.picks[0] or (self.kind == "cagr" and target[0] == self.picks[0][0])
        ):
            return None
        if self.kind == "gap" and self.picks and abs(target[0] - self.picks[0][0]) != 1:
            return None  # a gap opens between two adjacent categories
        self.picks.append(target)
        if len(self.picks) < 2:
            return None
        (start, start_series), (end, end_series) = self.picks
        if self.kind in ("gap", "bracket"):
            first, last = sorted((start, end))
            kind = "category_gap" if self.kind == "gap" else "group_bracket"
            return Annotation(kind, first, last)
        # Both ends must measure comparable things: two single series, or else the column totals.
        if start_series is not None and end_series is not None and start_series != end_series:
            return Annotation(
                self.kind, start, end, start_series, self.style, series_end=end_series
            )
        series = start_series if start_series == end_series else None
        return Annotation(self.kind, start, end, series, self.style)


def annotation_kind(kind: Literal["difference", "cagr", "gap", "bracket"]) -> AnnotationKind:
    """The annotation kind a pick session of ``kind`` creates."""
    if kind == "gap":
        return "category_gap"
    if kind == "bracket":
        return "group_bracket"
    return kind  # pyright: ignore[reportReturnType]  # a session and annotation kind share the name


def placed(state: ChartState, annotation: Annotation) -> Annotation:
    """The drawable form of a between-series difference arrow on ``state``.

    A bracket arrow connects two side-by-side bars, which only a clustered chart has: on a chart
    that stacks its series (stacked columns and bars, lines, a Mekko) it becomes a level difference.
    The other way round, a pie's segments meet at their arcs, so a level difference there becomes
    a bracket arrow. Every other annotation is drawn the way it was picked.
    """
    if annotation.kind != "difference" or annotation.start != annotation.end:
        return annotation
    if annotation.series is None:
        return annotation
    if (
        annotation.style == "bracket"
        and state.kind in ("column", "bar", "line", "mekko")
        and state.grouping == "stacked"
    ):
        return replace(annotation, style="level")
    if annotation.style == "level" and state.kind == "pie":
        return replace(annotation, style="bracket")
    return annotation


def supports(state: ChartState, kind: AnnotationKind) -> bool:
    if state.percent and not (state.kind == "mekko" and kind == "difference"):
        return False
    return kind in notes.SUPPORTED.get(state.kind, frozenset())
