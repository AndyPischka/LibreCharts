"""Layout of percent Marimekko charts.

Columns stand side by side with a narrow fixed gap; their widths are proportional to the column
widths, every column is 100 % high and its segments stack bottom-up in series order. Segments show
their share in percent, the width value stands above each column, the category name below, and the
series names to the right of the last column, level with its segments.

As in the other layouts the kinds and order of the primitives depend only on the data, never on
the size: a baseline, per column a bar and a label per series, a width label and a category name,
then one name per series. Labels that would not fit stay empty.
"""

from __future__ import annotations

from librecharts.core.layout.common import format_value
from librecharts.core.mekko import MekkoData
from librecharts.core.primitives import Line, Primitive, Rect, Text

TOP_BAND = 800.0  # room above the plot for the width labels
LABEL_HEIGHT = 600.0
CATEGORY_BAND = 1000.0  # room below the plot for category names
RIGHT_BAND = 2500.0  # room right of the plot for series names
LABEL_GAP = 150.0  # between the last column and the series names
COLUMN_GAP = 100.0  # fixed gap between columns, so equal colours of neighbours do not merge
MIN_SEGMENT_HEIGHT = 500.0  # flatter segments get no inside label
MIN_LABEL_WIDTH = 800.0  # narrower columns get no inside labels
MIN_OUTSIDE_LABEL_WIDTH = 1800.0  # width and category labels of narrow columns get wider boxes


def layout_mekko(data: MekkoData, width: float, height: float) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    categories, series = data.data.categories, data.data.series
    gaps = COLUMN_GAP * max(len(categories) - 1, 0)
    plot_width = width - RIGHT_BAND - gaps
    plot_height = height - TOP_BAND - CATEGORY_BAND
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not categories or not series:
        return ()

    total_width = sum(data.widths)
    plot_bottom = TOP_BAND + plot_height
    out: list[Primitive] = []
    column_x = 0.0
    last_segments: list[tuple[float, float]] = []  # (top, bottom) per series in the last column
    for c, category in enumerate(categories):
        column_width = plot_width * data.widths[c] / total_width if total_width > 0 else 0.0
        column_sum = sum(v for s in series if (v := s.values[c]) is not None)
        level = plot_bottom
        last_segments = []
        for i, s in enumerate(series):
            value = s.values[c] or 0.0
            share = value / column_sum if column_sum > 0 else 0.0
            segment_height = plot_height * share
            top = level - segment_height
            out.append(Rect(column_x, top, column_width, segment_height, i))
            fits = segment_height >= MIN_SEGMENT_HEIGHT and column_width >= MIN_LABEL_WIDTH
            label = f"{round(share * 100)}%" if fits and value > 0 else ""
            out.append(Text(column_x, top, column_width, segment_height, label, "center", "value"))
            last_segments.append((top, level))
            level = top
        # Outside labels of a narrow column get a wider box centred on it, so names do not wrap
        # letter by letter.
        box_x, box_width = _outside_box(column_x, column_width, width)
        out.append(
            Text(
                box_x,
                TOP_BAND - LABEL_HEIGHT,
                box_width,
                LABEL_HEIGHT,
                format_value(data.widths[c]),
                "center",
                "total",
            )
        )
        out.append(
            Text(box_x, plot_bottom, box_width, CATEGORY_BAND, category, "center", "category")
        )
        column_x += column_width + COLUMN_GAP

    plot_right = column_x - COLUMN_GAP
    out.insert(0, Line(0, plot_bottom, plot_right, plot_bottom, "baseline"))
    for (top, bottom), s in zip(last_segments, series, strict=True):
        middle = (top + bottom) / 2
        out.append(
            Text(
                plot_right + LABEL_GAP,
                middle - LABEL_HEIGHT / 2,
                RIGHT_BAND - LABEL_GAP,
                LABEL_HEIGHT,
                s.name,
                "left",
                "series",
            )
        )
    return tuple(out)


def _outside_box(x: float, width: float, limit: float) -> tuple[float, float]:
    """A label box at least ``MIN_OUTSIDE_LABEL_WIDTH`` wide, centred on the column."""
    if width >= MIN_OUTSIDE_LABEL_WIDTH:
        return x, width
    box_width = min(MIN_OUTSIDE_LABEL_WIDTH, limit)
    box_x = x + width / 2 - box_width / 2
    return min(max(box_x, 0.0), limit - box_width), box_width
