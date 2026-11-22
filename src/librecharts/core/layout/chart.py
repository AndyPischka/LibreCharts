"""Lay out a whole chart: pick the layout for the chart kind and apply display options."""

from __future__ import annotations

from librecharts.core import focus, labels, sorting
from librecharts.core.boxplot import parse as parse_boxplot
from librecharts.core.bullet import parse as parse_bullet
from librecharts.core.datasheet import ChartData, Series, errored, parse, ranged
from librecharts.core.gantt import parse_gantt
from librecharts.core.layout.area import layout_area
from librecharts.core.layout.bar import layout_bar
from librecharts.core.layout.boxplot import layout_boxplot
from librecharts.core.layout.bullet import layout_bullet
from librecharts.core.layout.butterfly import layout_butterfly
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.common import SOURCE_BAND, decorations
from librecharts.core.layout.dumbbell import layout_dumbbell
from librecharts.core.layout.funnel import layout_funnel
from librecharts.core.layout.gantt import layout_gantt
from librecharts.core.layout.line import layout_line
from librecharts.core.layout.matrix import layout_matrix
from librecharts.core.layout.mekko import layout_mekko
from librecharts.core.layout.pareto import layout_pareto
from librecharts.core.layout.pie import layout_pie
from librecharts.core.layout.scatter import layout_scatter
from librecharts.core.layout.table import layout_table
from librecharts.core.layout.waterfall import layout_waterfall
from librecharts.core.matrix import parse as parse_matrix
from librecharts.core.mekko import parse_mekko
from librecharts.core.model import Annotation, ChartState, Grouping
from librecharts.core.primitives import Primitive
from librecharts.core.scatter import parse_scatter
from librecharts.core.table import parse as parse_table
from librecharts.core.waterfall import parse_waterfall


def layout_chart(
    state: ChartState, width: float, height: float, length_per_unit: float | None = None
) -> tuple[Primitive, ...]:
    """Primitives for ``state`` in a ``width`` x ``height`` box (1/100 mm).

    Sorting applies to the display only: the layout gets the categories in display order and the
    annotations with their indices moved along, so the stored state never changes. A chart in a
    same-scale group passes the group's ``length_per_unit`` (ADR 0017).

    The label keys of the result name data sheet indices, and the offsets of moved labels in
    ``state.labels`` are applied (``core/labels.py``). Raises ``ValueError`` if the box is too small
    for the chart.
    """
    source_band = SOURCE_BAND if state.source else 0.0
    primitives = _layout(state, width, body_height(state, height), length_per_unit)
    if state.kind != "gantt":  # its texts stay where the layout puts them
        primitives = labels.place(labels.keyed(primitives, _order(state)), state.labels)
    primitives = focus.apply(primitives, state.focus)
    return primitives + tuple(decorations(state, width, height, source_band))


def body_height(state: ChartState, height: float) -> float:
    """The height the plot may use: the chart box minus the footer band of a source line."""
    return height - (SOURCE_BAND if state.source else 0.0)


def _order(state: ChartState) -> tuple[int, ...] | None:
    """The sort permutation of the categories, ``None`` if the chart is not sorted."""
    if state.sort == "none" or state.kind not in ("column", "bar", "butterfly"):
        return None
    return display_order(state)


def _layout(
    state: ChartState, width: float, height: float, length_per_unit: float | None
) -> tuple[Primitive, ...]:
    if state.kind == "waterfall":
        return layout_waterfall(
            parse_waterfall(state),
            width,
            height,
            state.annotations,
            state.format,
            length_per_unit,
            horizontal=state.horizontal,
        )
    if state.kind == "mekko":
        return layout_mekko(
            parse_mekko(state),
            width,
            height,
            state.percent,
            state.format,
            length_per_unit,
            state.annotations,
        )
    if state.kind == "scatter":
        return layout_scatter(
            parse_scatter(state),
            width,
            height,
            state.annotations,
            state.format,
            state.trends,
        )
    if state.kind == "table":
        return layout_table(parse_table(state), width, height, state.format)
    if state.kind == "matrix":
        return layout_matrix(parse_matrix(state), width, height, state.format)
    if state.kind == "bullet":
        return layout_bullet(parse_bullet(state), width, height, state.format)
    if state.kind == "boxplot":
        return layout_boxplot(parse_boxplot(state), width, height, state.format)
    if state.kind == "funnel":
        return layout_funnel(parse(state), width, height, state.format)
    if state.kind == "dumbbell":
        start_data, bases = ranged(state)
        if not bases:
            return ()
        dumbbell = ChartData(
            start_data.categories,
            (
                Series("Start", bases[0]),
                Series("End", start_data.series[0].values),
            ),
        )
        return layout_dumbbell(dumbbell, width, height, state.format, horizontal=state.horizontal)
    if state.kind == "gantt":
        return layout_gantt(
            parse_gantt(state, state.sort),
            width,
            height,
            state.annotations,
            state.format,
            state.calendar,
        )
    data, annotations = display_data(state)
    bases: tuple[tuple[float | None, ...], ...] | None = None
    errors: tuple[tuple[float | None, ...], ...] | None = None
    if state.range:  # floating bars: the to values as series, the from levels beside them
        data, bases, annotations = display_range(state)
    elif state.errors:  # error bars: the series values, the error magnitudes beside them
        data, errors, annotations = display_errored(state)
    if state.kind == "pie":
        return layout_pie(
            data,
            state.doughnut,
            width,
            height,
            state.format,
            state.annotations,
            state.sort,
        )
    if state.kind == "butterfly":
        return layout_butterfly(data, width, height, state.format, length_per_unit)
    if state.kind == "line":
        return layout_line(
            data,
            width,
            height,
            annotations,
            state.format,
            length_per_unit,
            errors=errors,
            trends=state.trends,
            interpolate=state.interpolate,
        )
    if state.kind == "area":
        return layout_area(
            data,
            state.grouping,
            width,
            height,
            annotations,
            percent=state.percent,
            fmt=state.format,
            length_per_unit=length_per_unit,
        )
    if state.pareto:
        return layout_pareto(data, width, height, state.format)
    if state.kind == "bar":
        return layout_bar(
            data,
            state.grouping,
            width,
            height,
            annotations,
            percent=state.percent,
            fmt=state.format,
            length_per_unit=length_per_unit,
            bases=bases,
            errors=errors,
        )
    return layout_column(
        data,
        state.grouping,
        width,
        height,
        annotations,
        percent=state.percent,
        fmt=state.format,
        lines=state.lines,
        secondary=state.secondary,
        length_per_unit=length_per_unit,
        bases=bases,
        errors=errors,
        trends=state.trends,
    )


def display_order(state: ChartState, data: ChartData | None = None) -> tuple[int, ...]:
    """Display position -> data sheet index of the categories."""
    if state.kind == "pie":  # a pie sorts its segments per pie, not its categories
        return tuple(range(len((data or parse(state)).categories)))
    # A butterfly chart sorts by its first series, like a clustered chart; floating bars are
    # drawn clustered whatever the stored grouping says, so they sort like a clustered chart.
    clustered = state.kind == "butterfly" or (state.range and state.kind in ("column", "bar"))
    grouped: Grouping = "clustered" if clustered else state.grouping
    return sorting.order(data or parse(state), grouped, state.sort)


def display_data(state: ChartState) -> tuple[ChartData, tuple[Annotation, ...]]:
    """The data in display order and the annotations moved along with it."""
    data = parse(state)
    order = display_order(state, data)
    if order == tuple(range(len(order))):
        return data, state.annotations
    return sorting.sorted_data(data, order), sorting.remap(state.annotations, order)


def display_range(
    state: ChartState,
) -> tuple[ChartData, tuple[tuple[float | None, ...], ...], tuple[Annotation, ...]]:
    """The floating-bar data in display order, the from levels and the annotations moved along."""
    data, bases = ranged(state)
    order = display_order(state, data)
    if order == tuple(range(len(order))):
        return data, bases, state.annotations
    return (
        sorting.sorted_data(data, order),
        tuple(tuple(base[i] for i in order) for base in bases),
        sorting.remap(state.annotations, order),
    )


def display_errored(
    state: ChartState,
) -> tuple[ChartData, tuple[tuple[float | None, ...], ...], tuple[Annotation, ...]]:
    """The error-bar data in display order, the error magnitudes and the annotations moved along."""
    data, errs = errored(state)
    order = display_order(state, data)
    if order == tuple(range(len(order))):
        return data, errs, state.annotations
    return (
        sorting.sorted_data(data, order),
        tuple(tuple(err[i] for i in order) for err in errs),
        sorting.remap(state.annotations, order),
    )
