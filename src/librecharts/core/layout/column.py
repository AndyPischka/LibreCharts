"""Layout of stacked and clustered column charts, also with single series as lines.

The kinds and order of the returned primitives depend only on the data and the format, never on the
size.

No value axis is drawn by default (like think-cell): values are labelled directly. With
``Format.axis`` a band left of the plot carries tick labels and, with ``gridlines``, light lines
behind the columns. Above the plot there is a band for total and value labels (and the legend),
below it a band for category labels. Bracket arrows (difference, CAGR) run in lanes above the label
band, one lane per arrow, the first one closest to the plot. Level arrows and value lines run in
lanes right of the plot, the first one closest to it.

A category gap (M14) widens the empty space between two adjacent categories; a group bracket runs
in a bracket lane above the plot and spans the centres of its categories, with its label above the
line. An arrow measures a (category, series?) pair at each end: a between-series arrow meets the
bars it measures, which stand side by side in a clustered chart.

An axis break removes a value range from the scale of the whole axis (core/axis_break.py): columns
reaching beyond it get a break mark and continue above it; labels keep the real values, ticks inside
the removed range are left out and the axis line gets a break mark.

A combination chart draws some series (``lines``) as lines instead of columns, optionally on a
secondary axis right of the plot (``secondary``). Line series do not stack, cluster or count as
column totals; their values only widen the scale of the axis they are drawn on.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.axis_break import Break, column_tops, resolve
from librecharts.core.axis_break import axis as shortened_axis
from librecharts.core.datasheet import ChartData, with_error_margins, with_from_levels
from librecharts.core.layout.common import (
    AXIS_BAND,
    GAP_RATIO,
    GAP_WIDTH,
    LABEL_HEIGHT,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    TICK_GAP,
    TICK_HEIGHT,
    bracket,
    column_top,
    format_value,
    group_bracket,
    legend,
    level_arrow,
    point_runs,
    slot_at,
    slot_start,
    spread,
    spread_back,
    value_axis,
    visible_ticks,
)
from librecharts.core.layout.common import (
    MIN_ARROW_LABEL_WIDTH as MIN_ARROW_LABEL_WIDTH,
)
from librecharts.core.model import Annotation, Format, Grouping, LabelKey
from librecharts.core.percent import column_total, negative_total
from librecharts.core.primitives import (
    BACKGROUND,
    Line,
    Marker,
    Polyline,
    Primitive,
    Rect,
    Text,
    TextRole,
)
from librecharts.core.rounding import consistent, consistent_shares
from librecharts.core.scale import Axis, nice_axis

PERCENT_AXIS = Axis(0.0, 100.0, 20.0)  # the fixed scale of a 100 % chart

TOP_BAND = 800.0  # room above the plot for total / outside value labels
CATEGORY_BAND = 1000.0  # room below the plot for category names
MIN_SEGMENT_FOR_LABEL = 500.0  # segments flatter than this get no inside label
LANE_HEIGHT = 800.0  # room for one arrow above the plot: its label and line
LANE_LINE_GAP = 100.0  # between an arrow's line and the bottom of its lane, or a column's label
SERIES_BAND = 2600.0  # room right of the lanes for series names
SERIES_LABEL_GAP = 150.0  # between the lanes and a series name
BREAK_GAP = 300.0  # height of the white gap of a break mark
BREAK_SLANT = 100.0  # how far the break lines fall from left to right
BREAK_OVERHANG = 100.0  # how far a break mark reaches beyond a stacked column
LINE_LABEL_GAP = 100.0  # between a line point and its value label
PICK_TOLERANCE = 900.0  # how far a click may miss a line point and still pick it, 1/100 mm
ERROR_CAP = 150.0  # half the width of an error bar's cap, 1/100 mm

_YScale = Callable[[float], float]


@dataclass(frozen=True, slots=True)
class _Geometry:
    """The plot rectangle and everything the layout derives from it.

    Shared by :func:`layout_column` and :func:`column_at`, so picking uses exactly the geometry
    that was drawn.
    """

    columns_data: ChartData  # the data with line series emptied: columns, totals, annotations
    plot_left: float
    top_band: float
    plot_width: float
    plot_height: float
    scale_height: float
    slot: float
    column_width: float
    axis: Axis
    secondary_axis: Axis | None
    cut: Break | None
    brackets: list[Annotation]
    levels: list[Annotation]
    value_lines: list[Annotation]
    gaps: list[Annotation]  # category gaps, in the order they were added
    groups: list[Annotation]  # group brackets, in the order they were added
    gap_starts: tuple[int, ...]  # the categories a gap opens after, sorted and unique
    line_series: tuple[int, ...]
    secondary_series: tuple[int, ...]
    columns: int
    bases: tuple[tuple[float | None, ...], ...] | None = None  # from levels of floating bars
    errors: tuple[tuple[float | None, ...], ...] | None = None  # error magnitudes per series
    length_per_unit: float | None = None


def layout_column(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    percent: bool = False,
    fmt: Format | None = None,
    lines: tuple[int, ...] = (),
    secondary: tuple[int, ...] = (),
    length_per_unit: float | None = None,
    bases: tuple[tuple[float | None, ...], ...] | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``percent`` the columns are 100 % high and the segments show their share; such a chart has
    no annotations (they stay stored but are neither drawn nor offered) and no line series.

    With ``bases`` the chart shows floating bars: each series is drawn between its from level
    (``bases[i][c]``, baseline when empty) and its to level (the series value), clustered like a
    clustered chart, and labelled with the to value outside the floating end.

    With ``errors`` every column gets a whisker with caps at value ± ``errors[i][c]``; the scale
    covers value ± error as well.

    ``lines`` draws those series as lines instead of columns; ``secondary`` puts a subset of them on
    a right-hand axis, which is drawn even without ``Format.axis``.

    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm and
    anchors the scale at the plot bottom, leaving empty space above the highest column. Such a chart
    ignores an axis break.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    geo = _geometry(
        data,
        grouping,
        width,
        height,
        annotations,
        percent,
        fmt,
        lines,
        secondary,
        length_per_unit,
        bases,
        errors,
    )
    if not data.categories or not data.series:
        return ()

    axis, cut = geo.axis, geo.cut
    span = axis.maximum - axis.minimum
    fold = cut.fold if cut else _same
    secondary = geo.secondary_series
    # Everything right of the plot starts behind the secondary axis's band, like the level
    # lanes of a bar chart start below its axis band: the axis numbers stay next to the plot.
    secondary_band = AXIS_BAND if geo.secondary_axis is not None else 0.0

    def y(value: float) -> float:
        """The y of a value already on the (folded) axis scale."""
        if geo.length_per_unit is not None:
            return geo.top_band + geo.scale_height - (value - axis.minimum) * geo.length_per_unit
        return geo.top_band + (axis.maximum - value) / span * geo.scale_height

    def y_data(value: float) -> float:
        """The y of a data value, folding the removed range of an axis break."""
        return y(fold(value))

    def y_secondary(value: float) -> float:
        other = geo.secondary_axis
        if other is None:  # no secondary values: nothing to draw, the primary scale is a stand-in
            return y(value)
        return (
            geo.top_band
            + (other.maximum - value) / (other.maximum - other.minimum) * geo.scale_height
        )

    slot, column_width = geo.slot, geo.column_width
    columns_data = geo.columns_data
    column_indices = tuple(i for i in range(len(data.series)) if i not in geo.line_series)

    def slot_x(category: int) -> float:
        """The left edge of ``category``'s slot, shifted by the category gaps before it."""
        return slot_start(geo.plot_left, category, slot, geo.gap_starts)

    def centre(category: int) -> float:
        """The centre of ``category``'s slot."""
        return slot_x(category) + slot / 2

    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in data.series], width))
    out.append(Line(geo.plot_left, y(0), geo.plot_left + geo.plot_width, y(0), "baseline"))
    if fmt.axis:
        out.extend(_grid(axis, cut, y, geo.plot_left, geo.plot_width) if fmt.gridlines else [])
        out.extend(_axis(axis, cut, y, geo.plot_left, fmt))
    if geo.secondary_axis is not None:
        out.extend(
            _right_axis(geo.secondary_axis, y_secondary, geo.plot_left + geo.plot_width, fmt)
        )

    for c, category in enumerate(data.categories):
        left = slot_x(c)
        column_x = left + (slot - column_width) / 2
        if geo.bases is not None:
            out.extend(
                _range_column(
                    columns_data, geo.bases, c, column_x, column_width, y, cut, fmt, geo.columns
                )
            )
        elif grouping == "stacked":
            out.extend(
                _stacked_column(
                    columns_data,
                    c,
                    column_x,
                    column_width,
                    y,
                    cut,
                    percent=percent,
                    fmt=fmt,
                    height=height,
                )
            )
        else:
            out.extend(
                _clustered_column(columns_data, c, column_x, column_width, y, cut, fmt, geo.columns)
            )
        if geo.errors is not None:
            out.extend(
                _column_error_bars(
                    columns_data,
                    geo.errors,
                    c,
                    column_x,
                    column_width,
                    y,
                    cut,
                    grouping,
                    geo.columns,
                )
            )
        out.append(
            Text(
                left,
                geo.top_band + geo.plot_height,
                slot,
                CATEGORY_BAND,
                category,
                "center",
                "category",
            )
        )

    for index in geo.line_series:
        scale = y_secondary if index in secondary else y_data
        out.extend(_line_series(data, index, centre, slot, scale, fmt))

    def edges(category: int, series: int | None) -> tuple[float, float]:
        """Left and right edge of the measured column, or of one bar of a clustered column."""
        column_x = slot_x(category) + (slot - column_width) / 2
        clustered = grouping == "clustered" or geo.bases is not None  # floating bars are clustered
        if series is not None and clustered and geo.columns:
            bar_width = column_width / geo.columns
            position = column_indices.index(series) if series in column_indices else 0
            return column_x + position * bar_width, column_x + (position + 1) * bar_width
        return column_x, column_x + column_width

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets what it measures: column top or line point, above it."""
        if series is not None and series in geo.line_series:
            value = notes.measured_value(data, category, series) or 0.0
            scale = y_secondary if series in secondary else y_data
            return centre(category), scale(value) - LABEL_HEIGHT - LANE_LINE_GAP
        left, right = edges(category, series)
        measured_grouping = "clustered" if geo.bases is not None else grouping
        return (left + right) / 2, y_data(
            column_top(columns_data, measured_grouping, category, series)
        ) - LABEL_HEIGHT - LANE_LINE_GAP

    def level(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge, at the measured value."""
        if series is not None and series in geo.line_series:
            value = notes.measured_value(data, category, series) or 0.0
            scale = y_secondary if series in secondary else y_data
            return centre(category), scale(value)
        value = notes.measured_value(columns_data, category, series) or 0.0
        return edges(category, series)[1], y_data(value)

    def measured_by(series: int | None, series_end: int | None = None) -> ChartData:
        """The data an arrow with these series indices measures: columns, or the line series."""
        end = series_end if series_end is not None else series
        for s in (series, end):
            if s is None or s not in geo.line_series:
                return columns_data
        return data

    def end_series(arrow: Annotation) -> int | None:
        """The series the arrow's end measures: its own, or the start's when it has none."""
        return arrow.series_end if arrow.series_end is not None else arrow.series

    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    lanes = (len(geo.brackets) + len(geo.groups)) * LANE_HEIGHT
    for lane, arrow in enumerate(geo.brackets):
        line_y = lanes_top + lanes - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, end_series(arrow)),
                line_y,
                notes.label(arrow, measured_by(arrow.series, arrow.series_end)),
            )
        )
    for lane, arrow in enumerate(geo.levels):
        arrow_x = (
            geo.plot_left
            + geo.plot_width
            + secondary_band
            + lane * LEVEL_LANE_WIDTH
            + LEVEL_ARROW_INSET
        )
        out.extend(
            level_arrow(
                level(arrow.start, arrow.series),
                level(arrow.end, end_series(arrow)),
                arrow_x,
                notes.label(arrow, measured_by(arrow.series, arrow.series_end)),
            )
        )
    for lane, group in enumerate(geo.groups):
        line_y = lanes_top + lanes - (len(geo.brackets) + lane) * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(group_bracket(centre(group.start), centre(group.end), line_y, group.text))
    for lane, annotation in enumerate(geo.value_lines):
        out.extend(
            _value_line(
                annotation,
                columns_data,
                y_data,
                geo.plot_left,
                geo.plot_width,
                secondary_band,
                len(geo.levels),
                lane,
                fmt,
            )
        )
    if fmt.series_names == "labels":
        band_x = (
            geo.plot_left
            + geo.plot_width
            + secondary_band
            + (len(geo.levels) + len(geo.value_lines)) * LEVEL_LANE_WIDTH
        )
        line_names = _line_name_tops(data, geo.line_series, secondary, slot, y_data, y_secondary)
        out.extend(
            _series_names(columns_data, grouping, column_indices, y_data, band_x, line_names)
        )
    return tuple(out)


def natural_length_per_unit(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    percent: bool = False,
    fmt: Format | None = None,
    lines: tuple[int, ...] = (),
    secondary: tuple[int, ...] = (),
    bases: tuple[tuple[float | None, ...], ...] | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size.

    ``None`` for a percent chart (it has a fixed 0..100 scale) or a box that is too small.
    """
    if percent:
        return None
    fmt = fmt or Format()
    try:
        geo = _geometry(
            data,
            grouping,
            width,
            height,
            annotations,
            False,
            fmt,
            lines,
            secondary,
            bases=bases,
            errors=errors,
        )
    except ValueError:
        return None
    span = geo.axis.maximum - geo.axis.minimum
    if span <= 0 or not data.categories or not data.series:
        return None
    return geo.scale_height / span


def _same(value: float) -> float:
    return value


def _geometry(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    percent: bool,
    fmt: Format,
    lines: tuple[int, ...],
    secondary: tuple[int, ...],
    length_per_unit: float | None = None,
    bases: tuple[tuple[float | None, ...], ...] | None = None,
    errors: tuple[tuple[float | None, ...], ...] | None = None,
) -> _Geometry:
    """Plot rectangle, axes and drawable annotations of a column chart."""
    line_set: frozenset[int] = (
        frozenset() if percent else frozenset(i for i in lines if 0 <= i < len(data.series))
    )
    secondary_set: frozenset[int] = frozenset(i for i in secondary if i in line_set)
    columns_data = _column_data(data, line_set)
    if percent:
        brackets, levels, value_lines, gaps, groups = [], [], [], [], []
    else:
        brackets, levels = notes.arrows(annotations, columns_data, "column")
        value_lines = notes.value_lines(annotations, columns_data, "column")
        gaps = notes.category_gaps(annotations, columns_data, "column")
        groups = notes.group_brackets(annotations, columns_data, "column")
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = lanes_top + (len(brackets) + len(groups)) * LANE_HEIGHT + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    right_lanes = len(levels) + len(value_lines)
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    secondary_axis = _secondary_axis(data, secondary_set)
    plot_width = (
        width
        - plot_left
        - right_lanes * LEVEL_LANE_WIDTH
        - series_band
        - (AXIS_BAND if secondary_axis is not None else 0.0)
    )
    plot_height = height - top_band - CATEGORY_BAND
    # Floating bars: the scale covers the from levels as well, and the bars measure clustered.
    # Error bars: the scale covers value ± error as well.
    if bases is not None:
        scale_data = with_from_levels(data, bases)
        scale_grouping: Grouping = "clustered"
    elif errors is not None:
        scale_data = with_error_margins(columns_data, errors)
        scale_grouping = grouping
    else:
        scale_data = columns_data
        scale_grouping = grouping
    has_negative = not percent and (
        any(v is not None and v < 0 for s in data.series for v in s.values)
        or any(v is not None and v < 0 for base in (bases or ()) for v in base)
    )
    # Labels of negative columns hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if has_negative else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")

    cut = (
        None
        if percent or length_per_unit is not None
        else resolve(annotations, scale_data, scale_grouping)
    )
    fold = cut.fold if cut else _same
    if percent:
        axis = PERCENT_AXIS
    elif not data.categories:
        axis = Axis(0.0, 1.0, 1.0)  # nothing to scale; the layout returns no primitives
    else:
        axis = (
            shortened_axis(scale_data, scale_grouping, cut)
            if cut
            else value_axis(scale_data, scale_grouping)
        )
    primary_lines = tuple(i for i in sorted(line_set) if i not in secondary_set)
    axis = _with_line_values(axis, data, primary_lines, fold)
    count = len(data.categories)
    gap_starts = tuple(sorted({gap.start for gap in gaps}))
    slot = (plot_width - GAP_WIDTH * len(gap_starts)) / count if count else 0.0
    if count and slot <= 0:
        raise ValueError("chart area too small")
    return _Geometry(
        columns_data=columns_data,
        plot_left=plot_left,
        top_band=top_band,
        plot_width=plot_width,
        plot_height=plot_height,
        scale_height=scale_height,
        slot=slot,
        column_width=slot * (1 - GAP_RATIO),
        axis=axis,
        secondary_axis=secondary_axis,
        cut=cut,
        brackets=brackets,
        levels=levels,
        value_lines=value_lines,
        gaps=gaps,
        groups=groups,
        gap_starts=gap_starts,
        line_series=tuple(sorted(line_set)),
        secondary_series=tuple(sorted(secondary_set)),
        columns=len(data.series) - len(line_set),
        bases=bases,
        errors=errors,
        length_per_unit=length_per_unit,
    )


def _column_data(data: ChartData, line_set: frozenset[int]) -> ChartData:
    """``data`` with the values of line series emptied, so only columns count anywhere."""
    if not line_set:
        return data
    empty = (None,) * len(data.categories)
    return replace(
        data,
        series=tuple(
            replace(series, values=empty) if i in line_set else series
            for i, series in enumerate(data.series)
        ),
    )


def _secondary_axis(data: ChartData, secondary: frozenset[int]) -> Axis | None:
    """The axis for the series drawn on the right, or ``None`` if they carry no value."""
    values = [
        value
        for index in sorted(secondary)
        for value in data.series[index].values
        if value is not None
    ]
    if not values:
        return None
    return nice_axis(min(values), max(values))


def _with_line_values(axis: Axis, data: ChartData, indices: Sequence[int], fold: _YScale) -> Axis:
    """Widen ``axis`` so that every primary line value fits into it."""
    values = [
        fold(value) for index in indices for value in data.series[index].values if value is not None
    ]
    if not values:
        return axis
    return nice_axis(min(axis.minimum, min(values)), max(axis.maximum, max(values)))


def _axis(
    axis: Axis,
    cut: Break | None,
    y: _YScale,
    plot_left: float,
    fmt: Format,
) -> list[Primitive]:
    """The axis line and its tick labels (the grid is emitted separately, behind the columns)."""
    out: list[Primitive] = [
        Line(plot_left, y(axis.maximum), plot_left, y(axis.minimum), "axis"),
    ]
    for tick in visible_ticks(axis, cut):
        top = y(cut.fold(tick) if cut else tick) - TICK_HEIGHT / 2
        out.append(
            Text(
                0,
                top,
                plot_left - TICK_GAP,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "right",
                "axis",
            )
        )
    if cut:
        out.extend(_axis_break_mark(plot_left, y(cut.lower)))
    return out


def _right_axis(axis: Axis, y: _YScale, x: float, fmt: Format) -> list[Primitive]:
    """The secondary axis line and its tick labels right of the plot."""
    out: list[Primitive] = [Line(x, y(axis.maximum), x, y(axis.minimum), "axis")]
    for tick in axis.ticks():
        out.append(
            Text(
                x + TICK_GAP,
                y(tick) - TICK_HEIGHT / 2,
                AXIS_BAND - TICK_GAP,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "left",
                "axis",
            )
        )
    return out


def _grid(
    axis: Axis, cut: Break | None, y: _YScale, plot_left: float, plot_width: float
) -> list[Primitive]:
    """Light lines behind the columns, one per tick except zero (the baseline covers it)."""
    return [
        Line(
            plot_left,
            y(cut.fold(tick) if cut else tick),
            plot_left + plot_width,
            y(cut.fold(tick) if cut else tick),
            "grid",
        )
        for tick in visible_ticks(axis, cut)
        if tick != 0
    ]


def _axis_break_mark(x: float, y_break: float) -> list[Primitive]:
    """A white gap and two slanted lines across the vertical axis line."""
    top = y_break - BREAK_GAP / 2
    return [
        Rect(x - BREAK_GAP / 2, top, BREAK_GAP, BREAK_GAP, BACKGROUND),
        Line(x - BREAK_GAP / 2, top, x + BREAK_GAP / 2, top + BREAK_SLANT, "axis"),
        Line(
            x - BREAK_GAP / 2,
            top + BREAK_GAP - BREAK_SLANT,
            x + BREAK_GAP / 2,
            top + BREAK_GAP,
            "axis",
        ),
    ]


def _value_line(
    annotation: Annotation,
    data: ChartData,
    y: _YScale,
    plot_left: float,
    plot_width: float,
    secondary_band: float,
    lanes: int,
    lane: int,
    fmt: Format,
) -> list[Primitive]:
    level = value_line.resolved(annotation, data)
    if level is None:
        return []
    line_y = y(level)
    label_x = (
        plot_left
        + plot_width
        + secondary_band
        + (lanes + lane) * LEVEL_LANE_WIDTH
        + LEVEL_ARROW_INSET
    )
    return [
        Line(plot_left, line_y, plot_left + plot_width, line_y, "helper"),
        Text(
            label_x,
            line_y - LABEL_HEIGHT / 2,
            LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
            LABEL_HEIGHT,
            format_value(level, fmt),
            "left",
            "annotation",
        ),
    ]


def _line_series(
    data: ChartData,
    index: int,
    centre: Callable[[int], float],
    slot: float,
    y: _YScale,
    fmt: Format,
) -> list[Primitive]:
    """One series drawn as a line: polyline runs, markers and a value label at every point."""
    series = data.series[index]
    points = [(centre(c), y(value)) for c, value in enumerate(series.values) if value is not None]
    out: list[Primitive] = [
        Polyline(tuple(run), index) for run in point_runs(points, series.values)
    ]
    if fmt.markers:
        out.extend(Marker(x, py, index) for x, py in points)
    for c, value in enumerate(series.values):
        if value is None:
            continue
        point_y = y(value)
        top = point_y - LABEL_HEIGHT - LINE_LABEL_GAP if value >= 0 else point_y + LINE_LABEL_GAP
        out.append(
            Text(
                centre(c) - slot / 2,
                top,
                slot,
                LABEL_HEIGHT,
                format_value(value, fmt),
                "center",
                "value",
                key=LabelKey("value", c, index),
            )
        )
    return out


def _line_name_tops(
    data: ChartData,
    line_series: Sequence[int],
    secondary: Sequence[int],
    slot: float,
    y: _YScale,
    y_secondary: _YScale,
) -> list[tuple[float, str]]:
    """Label positions for the line series, level with their last point."""
    out: list[tuple[float, str]] = []
    for index in line_series:
        series = data.series[index]
        last = next(
            (value for value in reversed(series.values) if value is not None),
            None,
        )
        if last is None:
            continue
        scale = y_secondary if index in secondary else y
        out.append((scale(last) - LABEL_HEIGHT / 2, series.name))
    return out


def _series_names(
    data: ChartData,
    grouping: Grouping,
    indices: Sequence[int],
    y: _YScale,
    band_x: float,
    extra: Sequence[tuple[float, str]] = (),
) -> list[Primitive]:
    """One series name per column series, level with the last column's segments or bars."""
    last = len(data.categories) - 1
    labelled: list[tuple[float, str]] = list(extra)
    if grouping == "stacked":
        positive = negative = 0.0
        for i in indices:
            series = data.series[i]
            value = series.values[last]
            if value is None or value == 0:
                top = bottom = y(positive + negative)
            elif value > 0:
                top, bottom = y(positive + value), y(positive)
                positive += value
            else:
                top, bottom = y(negative), y(negative + value)
                negative += value
            labelled.append(((top + bottom) / 2 - LABEL_HEIGHT / 2, series.name))
    else:
        for i in indices:
            series = data.series[i]
            value = series.values[last]
            top = y(value) if value is not None and value >= 0 else y(0.0)
            bottom = y(0.0) if value is not None and value >= 0 else y(value or 0.0)
            labelled.append(((top + bottom) / 2 - LABEL_HEIGHT / 2, series.name))
    # Bottom-up, so ``spread`` can move a box up when the one below it would overlap.
    labelled.sort(key=lambda item: item[0], reverse=True)
    tops = spread([top for top, _ in labelled], LABEL_HEIGHT)
    return [
        Text(
            band_x + SERIES_LABEL_GAP,
            top,
            SERIES_BAND - SERIES_LABEL_GAP,
            LABEL_HEIGHT,
            name,
            "left",
            "series",
        )
        for top, (_, name) in zip(tops, labelled, strict=True)
    ]


def break_mark(x: float, width: float, y_break: float, overhang: float) -> list[Primitive]:
    """A white gap across a column or bar with two parallel slanted lines."""
    left, right, top = x - overhang, x + width + overhang, y_break - BREAK_GAP / 2
    return [
        Rect(left, top, right - left, BREAK_GAP, BACKGROUND),
        Line(left, top, right, top + BREAK_SLANT, "annotation"),
        Line(left, top + BREAK_GAP - BREAK_SLANT, right, top + BREAK_GAP, "annotation"),
    ]


def column_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format | None = None,
    *,
    height: float | None = None,
    lines: tuple[int, ...] = (),
    secondary: tuple[int, ...] = (),
) -> tuple[int, int | None] | None:
    """The category (and, for a bar of a clustered chart, the series) at chart point (x, y).

    Uses the geometry of :func:`layout_column`. Points in the arrow lanes or outside the box hit
    nothing; between the bars of a clustered column, or on its labels below, the series is ``None``.

    With ``height`` and ``lines`` a click near a line point picks that series. Line values replace
    the bars of their series in a clustered chart.
    """
    fmt = fmt or Format()
    if height is not None and lines:
        target = _line_point_at(
            data, grouping, width, height, annotations, x, y, fmt, lines, secondary
        )
        if target is not None:
            return target
    line_set = frozenset(i for i in lines if 0 <= i < len(data.series))
    columns_data = _column_data(data, line_set)
    brackets, levels = notes.arrows(annotations, columns_data, "column")
    value_lines = notes.value_lines(annotations, columns_data, "column")
    gaps = notes.category_gaps(annotations, columns_data, "column")
    groups = notes.group_brackets(annotations, columns_data, "column")
    gap_starts = tuple(sorted({gap.start for gap in gaps}))
    lanes_top = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    plot_left = AXIS_BAND if fmt.axis else 0.0
    series_band = SERIES_BAND if fmt.series_names == "labels" else 0.0
    secondary_axis = _secondary_axis(data, frozenset(i for i in secondary if i in line_set))
    secondary_band = AXIS_BAND if secondary_axis is not None else 0.0
    plot_width = (
        width
        - plot_left
        - (len(levels) + len(value_lines)) * LEVEL_LANE_WIDTH
        - series_band
        - secondary_band
    )
    count = len(data.categories)
    slot = (
        (plot_width - GAP_WIDTH * len(gap_starts)) / count
        if count and plot_width > GAP_WIDTH * len(gap_starts)
        else 0.0
    )
    if (
        not data.categories
        or plot_width <= 0
        or slot <= 0
        or not plot_left <= x < plot_left + plot_width
        or y < lanes_top + (len(brackets) + len(groups)) * LANE_HEIGHT
    ):
        return None
    category = slot_at(plot_left, x, slot, count, gap_starts)
    if category is None:
        return None
    if grouping == "stacked" or not data.series:
        return category, None
    column_width = slot * (1 - GAP_RATIO)
    offset = x - slot_start(plot_left, category, slot, gap_starts) - (slot - column_width) / 2
    if not 0 <= offset < column_width:
        return category, None
    column_indices = [i for i in range(len(data.series)) if i not in line_set]
    if not column_indices:
        return category, None
    position = min(int(offset // (column_width / len(column_indices))), len(column_indices) - 1)
    return category, column_indices[position]


def _line_point_at(
    data: ChartData,
    grouping: Grouping,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format,
    lines: tuple[int, ...],
    secondary: tuple[int, ...],
) -> tuple[int, int] | None:
    """The line point (category, series) at chart point (x, y), or ``None``."""
    try:
        geo = _geometry(data, grouping, width, height, annotations, False, fmt, lines, secondary)
    except ValueError:
        return None
    if not geo.line_series or not data.categories:
        return None
    if (
        not geo.plot_left <= x < geo.plot_left + geo.plot_width
        or not geo.top_band <= y < geo.top_band + geo.plot_height
    ):
        return None
    category = slot_at(geo.plot_left, x, geo.slot, len(data.categories), geo.gap_starts)
    if category is None:
        return None
    best: tuple[float, int] | None = None
    for index in geo.line_series:
        value = data.series[index].values[category]
        if value is None:
            continue
        point_y = _line_point_y(geo, value, index in geo.secondary_series)
        distance = abs(y - point_y)
        if best is None or distance < best[0]:
            best = (distance, index)
    if best is None or best[0] > PICK_TOLERANCE:
        return None
    return category, best[1]


def _line_point_y(geo: _Geometry, value: float, secondary: bool) -> float:
    """The y of a line point: on the primary scale (folding the break) or the secondary one."""
    if secondary and geo.secondary_axis is not None:
        axis = geo.secondary_axis
        return geo.top_band + (axis.maximum - value) / (axis.maximum - axis.minimum) * (
            geo.scale_height
        )
    axis = geo.axis
    value = geo.cut.fold(value) if geo.cut else value
    if geo.length_per_unit is not None:
        return geo.top_band + geo.scale_height - (value - axis.minimum) * geo.length_per_unit
    return geo.top_band + (axis.maximum - value) / (axis.maximum - axis.minimum) * (
        geo.scale_height
    )


def _stacked_column(
    data: ChartData,
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    *,
    percent: bool = False,
    fmt: Format,
    height: float,
) -> list[Primitive]:
    if percent:
        return _percent_column(data, c, x, width, y, fmt)
    out: list[Primitive] = []
    column_top_value = column_tops(data, "stacked")[c]
    fold = cut.fold if cut else _same
    texts = consistent(
        [series.values[c] for series in data.series],
        sum(v for s in data.series if (v := s.values[c]) is not None),
        fmt,
    )
    positive = negative = 0.0
    segments = 0
    # The lanes of the labels that do not fit into their segment (M16): above the column's top
    # edge and below its bottom edge, one label height per slot. The total joins the lane of the
    # positive end unless the column has no positive segment.
    top_edge = y(fold(column_total(data, c)))
    bottom_edge = y(fold(negative_total(data, c)))
    above: list[tuple[int, Text]] = []  # (index into ``out``, label), one entry per lane slot
    below: list[tuple[int, Text]] = []

    def outside(
        text: str, role: TextRole, key: LabelKey, top: float, lane: list[tuple[int, Text]]
    ) -> None:
        """Append a lane label (plain text, no segment fill) and book its slot."""
        label = Text(x, top, width, LABEL_HEIGHT, text, "center", role, key=key)
        out.append(label)
        lane.append((len(out) - 1, label))

    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None or value == 0:
            continue
        segments += 1
        if value > 0:
            top, bottom = y(fold(positive + value)), y(fold(positive))
            positive += value
        else:
            top, bottom = y(fold(negative)), y(fold(negative + value))
            negative += value
        out.append(Rect(x, top, width, bottom - top, i))
        # Always emit the label right after its segment: the primitive structure must not depend
        # on the size, so a resized chart can be re-laid out in place (lo/render.py). A segment
        # too flat to hold its label gets a slot in the lane at its outer end instead (M16
        # decluttering).
        if bottom - top >= MIN_SEGMENT_FOR_LABEL:
            out.append(
                Text(
                    x,
                    top,
                    width,
                    bottom - top,
                    texts[i] or "",
                    "center",
                    "value",
                    fill=i,
                    key=LabelKey("value", c, i),
                )
            )
        elif value > 0:
            outside(
                texts[i] or "",
                "value",
                LabelKey("value", c, i),
                top_edge - LABEL_HEIGHT * (len(above) + 1),
                above,
            )
        else:
            outside(
                texts[i] or "",
                "value",
                LabelKey("value", c, i),
                bottom_edge + LABEL_HEIGHT * len(below),
                below,
            )
    if segments >= 2:  # a single segment's total would just repeat its own label
        total = format_value(positive + negative, fmt)
        if positive > 0.0:
            outside(
                total,
                "total",
                LabelKey("total", c),
                top_edge - LABEL_HEIGHT * (len(above) + 1),
                above,
            )
        else:
            outside(
                total, "total", LabelKey("total", c), bottom_edge + LABEL_HEIGHT * len(below), below
            )
    # A lane grows past the chart box with every label; it moves back as a whole instead — a
    # shape outside the box would grow the chart group on every redraw (test_layout_chart) —
    # and then covers the column it labels.
    tops = spread([label.y for _, label in above], LABEL_HEIGHT)
    for (index, label), top in zip(above, tops, strict=True):
        out[index] = replace(label, y=top)
    tops = spread_back([label.y for _, label in below], LABEL_HEIGHT, height)
    for (index, label), top in zip(below, tops, strict=True):
        out[index] = replace(label, y=top)
    if cut and cut.cuts(column_top_value):
        out.extend(break_mark(x, width, y(cut.lower), BREAK_OVERHANG))
    return out


def _percent_column(
    data: ChartData, c: int, x: float, width: float, y: _YScale, fmt: Format
) -> list[Primitive]:
    """A 100 % high column: shares inside, the absolute column sum above it."""
    total = column_total(data, c)
    if total <= 0:
        return []
    out: list[Primitive] = []
    level = 0.0
    percentages = consistent_shares([series.values[c] for series in data.series], total, fmt)
    above: list[tuple[int, Text]] = []  # (index into ``out``, label), one entry per lane slot

    def outside(text: str, role: TextRole, key: LabelKey, top: float) -> None:
        """Append a lane label (plain text, no segment fill) and book its slot."""
        label = Text(x, top, width, LABEL_HEIGHT, text, "center", role, key=key)
        out.append(label)
        above.append((len(out) - 1, label))

    for i, series in enumerate(data.series):
        value = series.values[c]
        percentage = percentages[i]
        if not percentage:
            continue
        height = (value or 0.0) / total * 100
        top, bottom = y(level + height), y(level)
        level += height
        out.append(Rect(x, top, width, bottom - top, i))
        # Always emit the label: the structure must not depend on the size. A segment too flat to
        # hold its label gets a slot in the lane above the column instead (M16 decluttering).
        if bottom - top >= MIN_SEGMENT_FOR_LABEL:
            out.append(
                Text(
                    x,
                    top,
                    width,
                    bottom - top,
                    percentage,
                    "center",
                    "value",
                    fill=i,
                    key=LabelKey("value", c, i),
                )
            )
        else:
            outside(
                percentage,
                "value",
                LabelKey("value", c, i),
                y(100.0) - LABEL_HEIGHT * (len(above) + 1),
            )
    outside(
        format_value(total, fmt),
        "total",
        LabelKey("total", c),
        y(100.0) - LABEL_HEIGHT * (len(above) + 1),
    )
    # A lane grows past the chart box with every label; it moves back as a whole instead — a
    # shape outside the box would grow the chart group on every redraw (test_layout_chart).
    tops = spread([label.y for _, label in above], LABEL_HEIGHT)
    for (index, label), top in zip(above, tops, strict=True):
        out[index] = replace(label, y=top)
    return out


def _clustered_column(
    data: ChartData,
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    fmt: Format,
    columns: int,
) -> list[Primitive]:
    if columns <= 0:
        return []
    out: list[Primitive] = []
    fold = cut.fold if cut else _same
    bar_width = width / columns
    drawn = 0
    for i, series in enumerate(data.series):
        value = series.values[c]
        if value is None:
            continue
        bar_x = x + drawn * bar_width
        drawn += 1
        top, bottom = (y(fold(value)), y(0)) if value >= 0 else (y(0), y(fold(value)))
        out.append(Rect(bar_x, top, bar_width, bottom - top, i))
        label_y = top - LABEL_HEIGHT if value >= 0 else bottom
        out.append(
            Text(
                bar_x,
                label_y,
                bar_width,
                LABEL_HEIGHT,
                format_value(value, fmt),
                "center",
                "value",
                key=LabelKey("value", c, i),
            )
        )
        if cut and cut.cuts(value):  # bars sit side by side: the mark stays on its bar
            out.extend(break_mark(bar_x, bar_width, y(cut.lower), 0.0))
    return out


def _column_error_bars(
    data: ChartData,
    errors: tuple[tuple[float | None, ...], ...],
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    grouping: Grouping,
    columns: int,
) -> list[Primitive]:
    """Whiskers with caps at value ± error over the columns of category ``c``.

    On a stacked column the whisker sits at the segment's outer (cumulative) level; on a clustered
    one at the top of its bar. An empty error cell draws no whisker for that point.
    """
    fold = cut.fold if cut else _same
    out: list[Primitive] = []
    if grouping == "stacked":
        positive = negative = 0.0
        for i, series in enumerate(data.series):
            value = series.values[c]
            if value is None or value == 0:
                continue
            level = positive + value if value > 0 else negative + value
            if value > 0:
                positive += value
            else:
                negative += value
            err = errors[i][c] if i < len(errors) else None
            if err:
                out.extend(_whisker(x + width / 2, level, err, y, fold))
    elif columns > 0:
        bar_width = width / columns
        drawn = 0
        for i, series in enumerate(data.series):
            value = series.values[c]
            if value is None:
                continue
            bar_x = x + drawn * bar_width
            drawn += 1
            err = errors[i][c] if i < len(errors) else None
            if err:
                out.extend(_whisker(bar_x + bar_width / 2, value, err, y, fold))
    return out


def _whisker(cx: float, value: float, err: float, y: _YScale, fold: _YScale) -> list[Primitive]:
    """A vertical whisker with caps from ``value - err`` to ``value + err`` at ``cx``."""
    top, bottom = y(fold(value + err)), y(fold(value - err))
    return [
        Line(cx, top, cx, bottom, "annotation"),
        Line(cx - ERROR_CAP, top, cx + ERROR_CAP, top, "annotation"),
        Line(cx - ERROR_CAP, bottom, cx + ERROR_CAP, bottom, "annotation"),
    ]


def _range_column(
    data: ChartData,
    bases: tuple[tuple[float | None, ...], ...],
    c: int,
    x: float,
    width: float,
    y: _YScale,
    cut: Break | None,
    fmt: Format,
    columns: int,
) -> list[Primitive]:
    """One category of floating bars: each series pair as a rect from its from to its to level.

    The bars sit side by side like a clustered column. The label shows the to value outside the
    floating end (above a rising bar, below a falling one); there is no total label.
    """
    if columns <= 0:
        return []
    fold = cut.fold if cut else _same
    bar_width = width / columns
    out: list[Primitive] = []
    for i, series in enumerate(data.series):
        to = series.values[c]
        if to is None:
            continue
        base = bases[i][c] if i < len(bases) else None
        base = 0.0 if base is None else base  # an empty from cell means the baseline
        bar_x = x + i * bar_width
        top, bottom = y(fold(max(to, base))), y(fold(min(to, base)))
        out.append(Rect(bar_x, top, bar_width, bottom - top, i))
        label_y = top - LABEL_HEIGHT if to >= base else bottom
        out.append(
            Text(
                bar_x,
                label_y,
                bar_width,
                LABEL_HEIGHT,
                format_value(to, fmt),
                "center",
                "value",
                key=LabelKey("value", c, i),
            )
        )
        if cut and (cut.cuts(to) or cut.cuts(base)):
            out.extend(break_mark(bar_x, bar_width, y(cut.lower), 0.0))
    return out
