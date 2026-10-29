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

As in the other layouts the kinds and order of the primitives depend only on the data and the
variant, never on the size: a baseline, per column a bar and a label per series and the outside
labels, then one name per series. Labels that would not fit stay empty.
"""

from __future__ import annotations

from librecharts.core.layout.common import (
    AXIS_BAND,
    LEGEND_HEIGHT,
    TICK_GAP,
    TICK_HEIGHT,
    format_share,
    format_value,
    legend,
    visible_ticks,
)
from librecharts.core.mekko import MekkoData
from librecharts.core.model import Format
from librecharts.core.primitives import Line, Primitive, Rect, Text, TextRole
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
    data: MekkoData, width: float, height: float, percent: bool = True, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box, as percent or units Mekko.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format(series_names="labels")
    categories, series = data.data.categories, data.data.series
    gaps = COLUMN_GAP * max(len(categories) - 1, 0)
    legend_band = LEGEND_HEIGHT if fmt.series_names == "legend" else 0.0
    top_band = TOP_BAND + legend_band
    labels = fmt.series_names == "labels"
    plot_left = AXIS_BAND if fmt.axis and not percent else 0.0
    plot_width = width - plot_left - (RIGHT_BAND if labels else 0.0) - gaps
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
            out.extend(_grid(axis, plot_bottom, plot_height, plot_left, plot_width))
        out.extend(_axis(axis, plot_bottom, plot_height, plot_left, fmt))
    column_x = plot_left
    last_segments: list[tuple[float, float]] = []  # (top, bottom) per series in the last column
    for c, category in enumerate(categories):
        column_width = plot_width * data.widths[c] / total_width if total_width > 0 else 0.0
        column_sum = sums[c]
        column_height = plot_height if percent else plot_height * column_sum / axis.maximum
        level = plot_bottom
        last_segments = []
        for i, s in enumerate(series):
            value = s.values[c] or 0.0
            share = value / column_sum if column_sum > 0 else 0.0
            segment_height = column_height * share
            top = level - segment_height
            out.append(Rect(column_x, top, column_width, segment_height, i))
            fits = segment_height >= MIN_SEGMENT_HEIGHT and column_width >= MIN_LABEL_WIDTH
            shown = format_share(share * 100, fmt) if percent else format_value(value, fmt)
            label = shown if fits and value > 0 else ""
            out.append(
                Text(column_x, top, column_width, segment_height, label, "center", "value", fill=i)
            )
            last_segments.append((top, level))
            level = top
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
                )
            )
        else:
            out.append(_label(box_x, level - LABEL_HEIGHT, box_width, column_sum, "total", fmt))
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
    if labels:
        name_tops = _spread(
            [(top + bottom) / 2 - LABEL_HEIGHT / 2 for top, bottom in last_segments]
        )
        for name_top, s in zip(name_tops, series, strict=True):
            out.append(
                Text(
                    plot_right + LABEL_GAP,
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
) -> list[Primitive]:
    def y(value: float) -> float:
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
) -> list[Primitive]:
    return [
        Line(
            plot_left,
            plot_bottom - plot_height * tick / axis.maximum,
            plot_left + plot_width,
            plot_bottom - plot_height * tick / axis.maximum,
            "grid",
        )
        for tick in visible_ticks(axis)
        if tick != 0
    ]


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


def _label(x: float, y: float, width: float, value: float, role: TextRole, fmt: Format) -> Text:
    return Text(x, y, width, LABEL_HEIGHT, format_value(value, fmt), "center", role)


def _outside_box(x: float, width: float, limit: float) -> tuple[float, float]:
    """A label box at least ``MIN_OUTSIDE_LABEL_WIDTH`` wide, centred on the column."""
    if width >= MIN_OUTSIDE_LABEL_WIDTH:
        return x, width
    box_width = min(MIN_OUTSIDE_LABEL_WIDTH, limit)
    box_x = x + width / 2 - box_width / 2
    return min(max(box_x, 0.0), limit - box_width), box_width
