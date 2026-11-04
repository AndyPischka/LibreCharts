"""Layout of Marimekko charts, percent and units variant (ADR 0012).

Columns stand side by side with a narrow fixed gap; their widths are proportional to the column
widths and their segments stack bottom-up in series order. The series names stand to the right of
the last column, level with its segments and moved apart where thin segments would make
them overlap.

- Percent: every column is 100 % high. Segments show their share in percent, the width value
  stands above each column, the category name below.
- Units: column heights are proportional to the column sums on a "nice" scale from zero. Segments
  show their absolute value, the column sum stands above each column, the category name below it
  and under that the width value.

Annotations (M14): bracket arrows (difference, CAGR) run in lanes above the width labels, level
arrows in lanes right of the last column, before the series names. An arrow end measures a segment
level (where the segment ends, so the label shows the segment's value or share) or, without a
series, the column top.

As in the other layouts the kinds and order of the primitives depend only on the data and the
variant, never on the size: a baseline, per column a bar and a label per series and the outside
labels, then one name per series. Labels that would not fit stay empty.
"""

from __future__ import annotations

from librecharts.core import annotations as notes
from librecharts.core.layout.column import LANE_HEIGHT, LANE_LINE_GAP
from librecharts.core.layout.common import (
    AXIS_BAND,
    LEGEND_HEIGHT,
    LEVEL_ARROW_INSET,
    LEVEL_LANE_WIDTH,
    TICK_GAP,
    TICK_HEIGHT,
    bracket,
    format_value,
    legend,
    level_arrow,
    visible_ticks,
)
from librecharts.core.mekko import MekkoData
from librecharts.core.mekko import levels as segment_values
from librecharts.core.model import Annotation, Format, LabelKey
from librecharts.core.primitives import Line, Primitive, Rect, Text, TextRole
from librecharts.core.rounding import consistent_shares
from librecharts.core.scale import Axis, nice_axis

TOP_BAND = 800.0  # room above the plot for the width labels
LABEL_HEIGHT = 600.0
CATEGORY_BAND = 1000.0  # room below the plot for category names
WIDTH_BAND = LABEL_HEIGHT  # units variant: extra room below the names for the width values
RIGHT_BAND = 2500.0  # room right of the plot for series names
LABEL_GAP = 150.0  # between the last column and the series names
COLUMN_GAP = 100.0  # fixed gap between columns, so equal colours of neighbours do not merge
MIN_SEGMENT_HEIGHT = 500.0  # flatter segments get no inside label
MIN_LABEL_WIDTH = 800.0  # narrower columns get no inside labels
MIN_OUTSIDE_LABEL_WIDTH = 1800.0  # width and category labels of narrow columns get wider boxes


def layout_mekko(
    data: MekkoData,
    width: float,
    height: float,
    percent: bool = True,
    fmt: Format | None = None,
    length_per_unit: float | None = None,
    annotations: tuple[Annotation, ...] = (),
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box, as percent or units Mekko.

    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm in
    the units variant, so a shorter column leaves empty space above it. A percent Mekko has a fixed
    0..100 scale and ignores it.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format(series_names="labels")
    if percent:
        length_per_unit = None
    categories, series = data.data.categories, data.data.series
    arrow_data = segment_values(data, percent)
    brackets, level_arrows = notes.arrows(annotations, arrow_data, "mekko")
    gaps = COLUMN_GAP * max(len(categories) - 1, 0)
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    bracket_lanes = len(brackets) * LANE_HEIGHT
    top_band = TOP_BAND + legend_band + bracket_lanes
    labels = fmt.series_names == "labels"
    plot_left = AXIS_BAND if fmt.axis and not percent else 0.0
    plot_width = (
        width
        - plot_left
        - (RIGHT_BAND if labels else 0.0)
        - len(level_arrows) * LEVEL_LANE_WIDTH
        - gaps
    )
    plot_height = height - top_band - CATEGORY_BAND - (0.0 if percent else WIDTH_BAND)
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not categories or not series:
        return ()

    total_width = sum(data.widths)
    sums = [
        sum(v for s in series if (v := s.values[c]) is not None) for c in range(len(categories))
    ]
    # Units: the "nice" scale from zero up to the tallest column; percent: no scale needed.
    axis = Axis(0.0, 1.0, 1.0) if percent else nice_axis(0.0, max(sums))
    plot_bottom = top_band + plot_height
    out: list[Primitive] = []
    if fmt.series_names == "legend":
        out.extend(legend([s.name for s in series], width))
    if fmt.axis and not percent:
        if fmt.gridlines:
            out.extend(
                _grid(axis, plot_bottom, plot_height, plot_left, plot_width, length_per_unit)
            )
        out.extend(_axis(axis, plot_bottom, plot_height, plot_left, fmt, length_per_unit))
    column_x = plot_left
    last_segments: list[tuple[float, float]] = []  # (top, bottom) per series in the last column
    column_bounds: list[tuple[float, float]] = []  # (x, width) per category
    segment_tops: list[list[float]] = []  # per category: the top y of each segment, bottom-up
    for c, category in enumerate(categories):
        column_width = plot_width * data.widths[c] / total_width if total_width > 0 else 0.0
        column_sum = sums[c]
        column_height = (
            plot_height
            if percent
            else (
                column_sum * length_per_unit
                if length_per_unit is not None
                else plot_height * column_sum / axis.maximum
            )
        )
        level = plot_bottom
        last_segments = []
        tops: list[float] = []
        percentages = (
            consistent_shares([s.values[c] for s in series], column_sum, fmt) if percent else None
        )
        for i, s in enumerate(series):
            value = s.values[c] or 0.0
            share = value / column_sum if column_sum > 0 else 0.0
            segment_height = column_height * share
            top = level - segment_height
            out.append(Rect(column_x, top, column_width, segment_height, i))
            fits = segment_height >= MIN_SEGMENT_HEIGHT and column_width >= MIN_LABEL_WIDTH
            shown = (percentages[i] or "") if percent else format_value(value, fmt)
            out.append(
                Text(
                    column_x,
                    top,
                    column_width,
                    segment_height,
                    shown,
                    "center",
                    "value",
                    fill=i,
                    key=LabelKey("value", c, i),
                    hidden=not (fits and value > 0),
                )
            )
            last_segments.append((top, level))
            tops.append(top)
            level = top
        segment_tops.append(tops)
        column_bounds.append((column_x, column_width))
        # Outside labels of a narrow column get a wider box centred on it, so names do not wrap
        # letter by letter.
        box_x, box_width = _outside_box(column_x, column_width, width)
        if percent:
            out.append(
                _label(
                    box_x,
                    top_band - LABEL_HEIGHT,
                    box_width,
                    data.widths[c],
                    "total",
                    fmt,
                    LabelKey("total", c),
                )
            )
        else:
            out.append(
                _label(
                    box_x,
                    level - LABEL_HEIGHT,
                    box_width,
                    column_sum,
                    "total",
                    fmt,
                    LabelKey("total", c),
                )
            )
        out.append(
            Text(box_x, plot_bottom, box_width, CATEGORY_BAND, category, "center", "category")
        )
        if not percent:
            out.append(
                _label(
                    box_x,
                    plot_bottom + CATEGORY_BAND,
                    box_width,
                    data.widths[c],
                    "value",
                    fmt,
                )
            )
        column_x += column_width + COLUMN_GAP

    plot_right = column_x - COLUMN_GAP
    out.insert(0, Line(plot_left, plot_bottom, plot_right, plot_bottom, "baseline"))

    def end_series(arrow: Annotation) -> int | None:
        """The series the arrow's end measures: its own, or the start's when it has none."""
        return arrow.series_end if arrow.series_end is not None else arrow.series

    def column_top_y(category: int) -> float:
        """The y of the column top: the level its last segment ends at."""
        return min(segment_tops[category], default=plot_bottom)

    def anchor(category: int, series: int | None) -> tuple[float, float]:
        """Where a bracket arrow meets what it measures: segment level or column top, above it."""
        bounds = column_bounds[category]
        x = bounds[0] + bounds[1] / 2
        top = segment_tops[category][series] if series is not None else column_top_y(category)
        return x, top - LABEL_HEIGHT - LANE_LINE_GAP

    def level_point(category: int, series: int | None) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge of the column, at the measured
        level."""
        bounds = column_bounds[category]
        top = segment_tops[category][series] if series is not None else column_top_y(category)
        return bounds[0] + bounds[1], top

    for lane, arrow in enumerate(brackets):
        line_y = legend_band + bracket_lanes - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(
                anchor(arrow.start, arrow.series),
                anchor(arrow.end, end_series(arrow)),
                line_y,
                notes.label(arrow, arrow_data),
            )
        )
    for lane, arrow in enumerate(level_arrows):
        arrow_x = plot_right + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(
                level_point(arrow.start, arrow.series),
                level_point(arrow.end, end_series(arrow)),
                arrow_x,
                notes.label(arrow, arrow_data),
            )
        )
    if labels:
        name_tops = _spread(
            [(top + bottom) / 2 - LABEL_HEIGHT / 2 for top, bottom in last_segments]
        )
        for name_top, s in zip(name_tops, series, strict=True):
            out.append(
                Text(
                    plot_right + len(level_arrows) * LEVEL_LANE_WIDTH + LABEL_GAP,
                    name_top,
                    RIGHT_BAND - LABEL_GAP,
                    LABEL_HEIGHT,
                    s.name,
                    "left",
                    "series",
                )
            )
    return tuple(out)


def _axis(
    axis: Axis,
    plot_bottom: float,
    plot_height: float,
    plot_left: float,
    fmt: Format,
    length_per_unit: float | None = None,
) -> list[Primitive]:
    def y(value: float) -> float:
        if length_per_unit is not None:
            return plot_bottom - length_per_unit * value
        return plot_bottom - plot_height * value / axis.maximum

    out: list[Primitive] = [Line(plot_left, y(axis.maximum), plot_left, y(0), "axis")]
    for tick in visible_ticks(axis):
        out.append(
            Text(
                0,
                y(tick) - TICK_HEIGHT / 2,
                plot_left - TICK_GAP,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "right",
                "axis",
            )
        )
    return out


def _grid(
    axis: Axis,
    plot_bottom: float,
    plot_height: float,
    plot_left: float,
    plot_width: float,
    length_per_unit: float | None = None,
) -> list[Primitive]:
    def y(value: float) -> float:
        if length_per_unit is not None:
            return plot_bottom - length_per_unit * value
        return plot_bottom - plot_height * value / axis.maximum

    return [
        Line(plot_left, y(tick), plot_left + plot_width, y(tick), "grid")
        for tick in visible_ticks(axis)
        if tick != 0
    ]


def natural_length_per_unit(
    data: MekkoData,
    width: float,
    height: float,
    percent: bool = True,
    fmt: Format | None = None,
    annotations: tuple[Annotation, ...] = (),
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size.

    ``None`` for the percent variant (fixed 0..100 scale) or a box that is too small.
    """
    if percent:
        return None
    fmt = fmt or Format(series_names="labels")
    categories, series = data.data.categories, data.data.series
    arrow_data = segment_values(data, False)
    brackets, level_arrows = notes.arrows(annotations, arrow_data, "mekko")
    gaps = COLUMN_GAP * max(len(categories) - 1, 0)
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = TOP_BAND + legend_band + len(brackets) * LANE_HEIGHT
    labels = fmt.series_names == "labels"
    plot_left = AXIS_BAND if fmt.axis else 0.0
    plot_width = (
        width
        - plot_left
        - (RIGHT_BAND if labels else 0.0)
        - len(level_arrows) * LEVEL_LANE_WIDTH
        - gaps
    )
    plot_height = height - top_band - CATEGORY_BAND - WIDTH_BAND
    if plot_width <= 0 or plot_height <= 0 or not categories or not series:
        return None
    sums = [
        sum(v for s in series if (v := s.values[c]) is not None) for c in range(len(categories))
    ]
    axis = nice_axis(0.0, max(sums))
    if axis.maximum <= 0:
        return None
    return plot_height / axis.maximum


def mekko_at(
    data: MekkoData,
    width: float,
    height: float,
    percent: bool,
    x: float,
    y: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[int, int | None] | None:
    """The column (and the segment) at chart point (x, y), or ``None``.

    Uses the geometry of :func:`layout_mekko`; annotations reserve their lanes, so a click there
    hits nothing. A click between segments of a column picks the column as a whole. Segment shares
    do not change with the shared scale of a same-scale group, so the hit test needs no
    ``length_per_unit``.
    """
    fmt = fmt or Format(series_names="labels")
    categories, series = data.data.categories, data.data.series
    arrow_data = segment_values(data, percent)
    brackets, level_arrows = notes.arrows(annotations, arrow_data, "mekko")
    gaps = COLUMN_GAP * max(len(categories) - 1, 0)
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = TOP_BAND + legend_band + len(brackets) * LANE_HEIGHT
    labels = fmt.series_names == "labels"
    plot_left = AXIS_BAND if fmt.axis and not percent else 0.0
    plot_width = (
        width
        - plot_left
        - (RIGHT_BAND if labels else 0.0)
        - len(level_arrows) * LEVEL_LANE_WIDTH
        - gaps
    )
    plot_height = height - top_band - CATEGORY_BAND - (0.0 if percent else WIDTH_BAND)
    if not categories or not series or plot_width <= 0 or plot_height <= 0:
        return None
    plot_bottom = top_band + plot_height
    if not top_band <= y < plot_bottom:
        return None
    total_width = sum(data.widths)
    sums = [
        sum(v for s in series if (v := s.values[c]) is not None) for c in range(len(categories))
    ]
    axis = Axis(0.0, 1.0, 1.0) if percent else nice_axis(0.0, max(sums))
    column_x = plot_left
    for c, _column in enumerate(categories):
        column_width = plot_width * data.widths[c] / total_width if total_width > 0 else 0.0
        if column_x <= x < column_x + column_width:
            column_sum = sums[c]
            column_height = plot_height if percent else plot_height * column_sum / axis.maximum
            level = plot_bottom
            for i, s in enumerate(series):
                value = s.values[c] or 0.0
                share = value / column_sum if column_sum > 0 else 0.0
                segment_height = column_height * share
                if segment_height > 0 and level - segment_height <= y < level:
                    return c, i
                level -= segment_height
            return c, None
        column_x += column_width + COLUMN_GAP
    return None


def _spread(tops: list[float]) -> list[float]:
    """Move name boxes (listed bottom-up, like the series) apart so none overlaps the next.

    Each box keeps its place if it can; a box that would touch the one below moves up. If the
    stack then reaches above the chart, it moves down as a whole.
    """
    spread: list[float] = []
    for top in tops:
        spread.append(min(top, spread[-1] - LABEL_HEIGHT) if spread else top)
    overshoot = min(spread, default=0.0)
    return [top - min(overshoot, 0.0) for top in spread]


def _label(
    x: float,
    y: float,
    width: float,
    value: float,
    role: TextRole,
    fmt: Format,
    key: LabelKey | None = None,
) -> Text:
    return Text(x, y, width, LABEL_HEIGHT, format_value(value, fmt), "center", role, key=key)


def _outside_box(x: float, width: float, limit: float) -> tuple[float, float]:
    """A label box at least ``MIN_OUTSIDE_LABEL_WIDTH`` wide, centred on the column."""
    if width >= MIN_OUTSIDE_LABEL_WIDTH:
        return x, width
    box_width = min(MIN_OUTSIDE_LABEL_WIDTH, limit)
    box_x = x + width / 2 - box_width / 2
    return min(max(box_x, 0.0), limit - box_width), box_width
