"""Pieces shared by the layouts: number formatting, axes, legends and series labels."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from librecharts.core.datasheet import ChartData
from librecharts.core.format import magnitude_suffix
from librecharts.core.model import ChartState, Format, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, manual_axis, nice_axis

if TYPE_CHECKING:
    from librecharts.core.axis_break import Break

GAP_RATIO = 0.3  # share of a category slot left empty between columns or bars
GAP_WIDTH = 500.0  # the wider empty space a category gap opens between two slots (M14)
BRACKET_TICK = 200.0  # how far the end ticks of a group bracket drop below its line

AXIS_BAND = 1600.0  # room left of (below, for bars) the plot for tick labels
AXIS_TITLE_BAND = 700.0  # room for a rotated value-axis title or a category-axis title
TICK_HEIGHT = 500.0  # height of one tick label box
TICK_GAP = 100.0  # between the plot edge and the tick label
LEGEND_HEIGHT = 800.0  # band above (or below) the plot for a horizontal legend
LEGEND_COLUMN = 2600.0  # band left or right of the plot for a vertical legend
LEGEND_ROW = 600.0  # height of one entry of a vertical legend
SWATCH = 250.0  # legend colour swatch
SWATCH_GAP = 120.0  # between a legend swatch and its text
SOURCE_BAND = 900.0  # footer band reserved by a chart-level source line
NOTE_WIDTH = 5000.0  # width of a free callout text box
NOTE_HEIGHT = 600.0  # height of a free callout text box
AXIS_BREAK_GAP = 300.0  # height of the white gap of a vertical axis break mark
AXIS_BREAK_SLANT = 100.0  # how far the break lines fall from left to right

LABEL_HEIGHT = 600.0  # height of a value, total or annotation label box
MIN_ARROW_LABEL_WIDTH = 1800.0  # arrows between neighbouring narrow columns stay readable
LEVEL_LANE_WIDTH = 2000.0  # room right of the plot for one level arrow or value line and its label
LEVEL_ARROW_INSET = 300.0  # from a level lane's left edge to its arrow
LEVEL_LABEL_GAP = 150.0  # between a level arrow or value line and its label


def format_value(value: float, fmt: Format | None = None) -> str:
    """The label text for ``value`` under ``fmt`` (decimals, magnitude, unit, separator)."""
    fmt = fmt or Format()
    scaled = value / 10**fmt.magnitude
    text = _number(scaled, fmt.decimals)
    if fmt.separator == ",":
        text = text.replace(".", ",")
    suffix = magnitude_suffix(fmt.magnitude, fmt.language)
    if suffix:
        text = f"{text} {suffix}"
    if fmt.unit:
        text = f"{text} {fmt.unit}"
    return text


def format_share(value: float, fmt: Format | None = None) -> str:
    """A percentage label (``33.3%``): decimals and separator, never magnitude or unit."""
    fmt = fmt or Format()
    decimals = 1 if fmt.decimals is None else fmt.decimals
    text = f"{value:.{decimals}f}"
    if fmt.decimals is None:
        text = text.rstrip("0").rstrip(".") or "0"
    if fmt.separator == ",":
        text = text.replace(".", ",")
    return text + "%"


def _number(value: float, decimals: int | None) -> str:
    if value == 0:  # no "-0"
        value = 0.0
    if decimals is None:
        if value == round(value):
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".") or "0"
    return f"{value:.{decimals}f}"


def column_top(data: ChartData, grouping: Grouping, category: int, series: int | None) -> float:
    """The highest value of a column (or of one bar of a clustered one); 0 if it only goes down."""
    values = [v for s in data.series if (v := s.values[category]) is not None]
    if series is not None and grouping == "clustered":
        return max(data.series[series].values[category] or 0.0, 0.0)
    if grouping == "clustered":
        return max([0.0, *values])
    return sum(v for v in values if v > 0)


def value_axis(
    data: ChartData,
    grouping: Grouping,
    fmt: Format | None = None,
    *,
    include_zero: bool = True,
) -> Axis:
    """The value range of the data, with the format's manual limits and scale (M23).

    ``include_zero`` keeps the baseline visible, which column and bar charts need. A logarithmic
    axis rejects non-positive data: the dialog never lets the user switch such a chart.
    """
    fmt = fmt or Format()
    if grouping == "stacked":
        lows: list[float] = []
        highs: list[float] = []
        for c in range(len(data.categories)):
            column = [v for s in data.series if (v := s.values[c]) is not None]
            lows.append(sum(v for v in column if v < 0))
            highs.append(sum(v for v in column if v > 0))
    else:
        values = [v for s in data.series for v in s.values if v is not None]
        lows = [min(values, default=0.0)]
        highs = [max(values, default=0.0)]
    low, high = min(lows, default=0.0), max(highs, default=0.0)
    if fmt.axis_scale == "log":
        positive = [v for v in (*lows, *highs) if v > 0]
        if not positive or low <= 0 or high <= 0:
            raise ValueError("a logarithmic axis needs positive data")
        fallback = Axis(low, high, _log_step(low, high), "log")
    else:
        fallback = nice_axis(low, high, include_zero=include_zero)
    if fmt.axis_min is None and fmt.axis_max is None and fmt.axis_scale == "linear":
        return fallback
    return manual_axis(
        fmt.axis_min,
        fmt.axis_max,
        fmt.axis_step,
        scale=fmt.axis_scale,
        fallback=fallback,
    )


def _log_step(low: float, high: float) -> float:
    """A representative step of a log axis, used when the user did not give one."""
    return max(10.0 ** math.floor(math.log10(low)), (high - low) / 5)


def axis_title(
    fmt: Format, x: float, y: float, width: float, height: float, *, rotated: bool
) -> list[Primitive]:
    """The value-axis title in a band left of (or below) the plot (M23)."""
    if not fmt.axis_title:
        return []
    return [
        Text(x, y, width, height, fmt.axis_title, "center", "axis", rotation=90 if rotated else 0)
    ]


def category_title(fmt: Format, x: float, y: float, width: float) -> list[Primitive]:
    """The category-axis title below the category names (M23)."""
    if not fmt.category_axis_title:
        return []
    return [
        Text(
            x,
            y,
            width,
            AXIS_TITLE_BAND,
            fmt.category_axis_title,
            "center",
            "axis",
        )
    ]


def baseline_cut(x: float, y: float, *, vertical: bool = True) -> list[Primitive]:
    """A small cut mark at the foot of an axis that starts above zero (M23)."""
    size = 250.0
    if vertical:
        return [
            Rect(x - size / 2, y - size / 2, size, size, BACKGROUND),
            Line(x - size / 2, y + size / 2, x + size / 2, y - size / 2, "axis"),
        ]
    return [
        Rect(x - size / 2, y - size / 2, size, size, BACKGROUND),
        Line(x + size / 2, y - size / 2, x - size / 2, y + size / 2, "axis"),
    ]


def visible_ticks(axis: Axis, cut: Break | None = None) -> list[float]:
    """The tick values to label; ticks inside an axis break's removed range are left out."""
    return [t for t in axis.ticks() if cut is None or not (cut.lower < t < cut.upper)]


def legend_insets(fmt: Format | None = None) -> tuple[float, float, float, float]:
    """Left, top, right and bottom space a chart's legend takes from the plot box."""
    fmt = fmt or Format()
    if fmt.series_names != "legend":
        return 0.0, 0.0, 0.0, 0.0
    if fmt.legend == "bottom":
        return 0.0, 0.0, 0.0, LEGEND_HEIGHT
    if fmt.legend == "left":
        return LEGEND_COLUMN, 0.0, 0.0, 0.0
    if fmt.legend == "right":
        return 0.0, 0.0, LEGEND_COLUMN, 0.0
    return 0.0, LEGEND_HEIGHT, 0.0, 0.0


def legend(
    names: Sequence[str], width: float, position: str = "top", height: float = 0.0
) -> list[Primitive]:
    """A legend in ``position``: horizontal above or below the plot, or a vertical column.

    The caller reserves the band with :func:`legend_insets`; ``width`` and ``height`` are the full
    chart box, so the legend lands on the correct edge.
    """
    if not names:
        return []
    if position in ("left", "right"):
        x = 0.0 if position == "left" else width - LEGEND_COLUMN
        row = min(LEGEND_ROW, height / len(names)) if height else LEGEND_ROW
        out: list[Primitive] = []
        for i, name in enumerate(names):
            top = i * row + (row - SWATCH) / 2
            out.append(Rect(x, top, SWATCH, SWATCH, i))
            out.append(
                Text(
                    x + SWATCH + SWATCH_GAP,
                    top,
                    max(LEGEND_COLUMN - SWATCH - SWATCH_GAP, 0.0),
                    SWATCH,
                    name,
                    "left",
                    "series",
                )
            )
        return out
    entry = width / len(names)
    top = (
        height - LEGEND_HEIGHT + (LEGEND_HEIGHT - SWATCH) / 2
        if position == "bottom"
        else (LEGEND_HEIGHT - SWATCH) / 2
    )
    out = []
    for i, name in enumerate(names):
        x = i * entry
        out.append(Rect(x, top, SWATCH, SWATCH, i))
        out.append(
            Text(
                x + SWATCH + SWATCH_GAP,
                top,
                max(entry - SWATCH - SWATCH_GAP, 0.0),
                SWATCH,
                name,
                "left",
                "series",
            )
        )
    return out


def decorations(
    state: ChartState, width: float, height: float, source_band: float
) -> list[Primitive]:
    """The source line and free notes of ``state`` (M22).

    ``source_band`` is the footer reserved for the source; notes are anchored at fractions of the
    full layout box, so they stay where the author put them when the chart is resized.
    """
    out: list[Primitive] = []
    if state.source:
        out.append(
            Text(
                0.0,
                height - source_band,
                width,
                source_band,
                state.source,
                "left",
                "axis",
            )
        )
    for index, note in enumerate(state.notes):
        out.append(
            Text(
                note.x * width,
                note.y * height,
                NOTE_WIDTH,
                NOTE_HEIGHT,
                note.text,
                "left",
                "note",
                name=f"librecharts-note:{index}",
            )
        )
    return out


def vertical_axis(
    axis: Axis,
    cut: Break | None,
    y: Callable[[float], float],
    plot_left: float,
    fmt: Format,
) -> list[Primitive]:
    """The vertical axis line, its tick labels and a break mark (line and area charts)."""
    out: list[Primitive] = [Line(plot_left, y(axis.maximum), plot_left, y(axis.minimum), "axis")]
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
        out.extend(vertical_break_mark(plot_left, y(cut.lower)))
    return out


def vertical_grid(
    axis: Axis,
    cut: Break | None,
    y: Callable[[float], float],
    plot_left: float,
    plot_width: float,
) -> list[Primitive]:
    """Light lines behind the plot, one per tick except zero (the baseline covers it)."""
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


def vertical_break_mark(x: float, y_break: float) -> list[Primitive]:
    """A white gap and two slanted lines across a vertical axis line."""
    top = y_break - AXIS_BREAK_GAP / 2
    return [
        Rect(x - AXIS_BREAK_GAP / 2, top, AXIS_BREAK_GAP, AXIS_BREAK_GAP, BACKGROUND),
        Line(x - AXIS_BREAK_GAP / 2, top, x + AXIS_BREAK_GAP / 2, top + AXIS_BREAK_SLANT, "axis"),
        Line(
            x - AXIS_BREAK_GAP / 2,
            top + AXIS_BREAK_GAP - AXIS_BREAK_SLANT,
            x + AXIS_BREAK_GAP / 2,
            top + AXIS_BREAK_GAP,
            "axis",
        ),
    ]


def bracket(
    start: tuple[float, float], end: tuple[float, float], line_y: float, label: str
) -> list[Primitive]:
    """Up from ``start``, across at ``line_y``, down onto ``end`` with an arrowhead."""
    (x1, y1), (x2, y2) = start, end
    left, right = min(x1, x2), max(x1, x2)
    label_width = max(right - left, MIN_ARROW_LABEL_WIDTH)
    return [
        Line(x1, line_y, x1, y1, "annotation"),
        Line(left, line_y, right, line_y, "annotation"),
        Line(x2, line_y, x2, y2, "annotation", arrow=True),
        Text(
            (left + right - label_width) / 2,
            line_y - LABEL_HEIGHT,
            label_width,
            LABEL_HEIGHT,
            label,
            "center",
            "annotation",
        ),
    ]


def level_arrow(
    start: tuple[float, float], end: tuple[float, float], arrow_x: float, label: str
) -> list[Primitive]:
    """Dashed lines from both levels to ``arrow_x``, an arrow from one level to the other."""
    (x1, y1), (x2, y2) = start, end
    return [
        Line(x1, y1, arrow_x, y1, "helper"),
        Line(x2, y2, arrow_x, y2, "helper"),
        Line(arrow_x, y1, arrow_x, y2, "annotation", arrow=True),
        Text(
            arrow_x + LEVEL_LABEL_GAP,
            (y1 + y2 - LABEL_HEIGHT) / 2,
            LEVEL_LANE_WIDTH - LEVEL_ARROW_INSET - LEVEL_LABEL_GAP,
            LABEL_HEIGHT,
            label,
            "left",
            "annotation",
        ),
    ]


def group_bracket(left: float, right: float, line_y: float, label: str) -> list[Primitive]:
    """A bracket over the categories from ``left`` to ``right``, its label above the line."""
    label_width = max(right - left, MIN_ARROW_LABEL_WIDTH)
    out: list[Primitive] = [
        Line(left, line_y, left, line_y + BRACKET_TICK, "annotation"),
        Line(left, line_y, right, line_y, "annotation"),
        Line(right, line_y, right, line_y + BRACKET_TICK, "annotation"),
    ]
    if label:
        out.append(
            Text(
                (left + right - label_width) / 2,
                line_y - LABEL_HEIGHT,
                label_width,
                LABEL_HEIGHT,
                label,
                "center",
                "annotation",
            )
        )
    return out


def slot_start(origin: float, index: int, slot: float, gap_starts: Sequence[int]) -> float:
    """The left (top, for bars) edge of category ``index``'s slot.

    ``gap_starts`` are the categories a category gap opens after (M14): every gap before
    ``index`` shifts the slot by :data:`GAP_WIDTH`.
    """
    return origin + index * slot + GAP_WIDTH * sum(1 for g in gap_starts if g < index)


def slot_at(
    origin: float, position: float, slot: float, count: int, gap_starts: Sequence[int]
) -> int | None:
    """The category whose slot contains ``position``, or ``None`` between or outside them."""
    for c in range(count):
        start = slot_start(origin, c, slot, gap_starts)
        if start <= position < start + slot:
            return c
    return None


def point_runs(
    points: Sequence[tuple[float, float]], values: Sequence[float | None]
) -> list[list[tuple[float, float]]]:
    """Split ``points`` where ``values`` is empty, so a gap breaks a polyline."""
    runs: list[list[tuple[float, float]]] = []
    run: list[tuple[float, float]] = []
    position = 0
    for value in values:
        if value is None:
            if run:
                runs.append(run)
                run = []
            continue
        run.append(points[position])
        position += 1
    if run:
        runs.append(run)
    return runs


def spread(tops: list[float], height: float) -> list[float]:
    """Move label boxes (listed bottom-up) apart so that none overlaps the next.

    Each box keeps its place if it can; a box that would touch the one below moves up. If the
    stack then reaches above the chart, it moves down as a whole. Shared by the Mekko, the
    flat label lanes and the line and pie layouts.
    """
    spread_tops: list[float] = []
    for top in tops:
        spread_tops.append(min(top, spread_tops[-1] - height) if spread_tops else top)
    overshoot = min(spread_tops, default=0.0)
    return [top - min(overshoot, 0.0) for top in spread_tops]


def spread_back(starts: list[float], size: float, limit: float) -> list[float]:
    """Shift a lane of label boxes back into the chart as a whole.

    The mirror of :func:`spread`'s whole-stack shift for a lane that grows toward larger
    coordinates (down, or right): the flat label lanes pitch their boxes at a fixed distance,
    so none overlaps another, but the outermost box grows past the chart box with every label.
    The lane keeps its pitch and moves back so the outermost box ends at ``limit`` (the
    chart's height or width); it can then cover the column or bar it labels. A shape outside
    the box would grow the chart group on every redraw instead (test_layout_chart).
    """
    shift = max(0.0, max(starts, default=0.0) + size - limit)
    return [start - shift for start in starts]
