"""Pieces shared by the layouts: number formatting, axes, legends and series labels."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from librecharts.core.datasheet import ChartData
from librecharts.core.format import magnitude_suffix
from librecharts.core.model import Format, Grouping
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, nice_axis

if TYPE_CHECKING:
    from librecharts.core.axis_break import Break

GAP_RATIO = 0.3  # share of a category slot left empty between columns or bars

AXIS_BAND = 1600.0  # room left of (below, for bars) the plot for tick labels
TICK_HEIGHT = 500.0  # height of one tick label box
TICK_GAP = 100.0  # between the plot edge and the tick label
LEGEND_HEIGHT = 800.0  # band above the plot for a legend
SWATCH = 250.0  # legend colour swatch
SWATCH_GAP = 120.0  # between a legend swatch and its text
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


def value_axis(data: ChartData, grouping: Grouping) -> Axis:
    """The value range covering all segments (stacked: per-category sums), always including zero."""
    if grouping == "stacked":
        lows: list[float] = []
        highs: list[float] = []
        for c in range(len(data.categories)):
            column = [v for s in data.series if (v := s.values[c]) is not None]
            lows.append(sum(v for v in column if v < 0))
            highs.append(sum(v for v in column if v > 0))
        return nice_axis(min(lows), max(highs))
    values = [v for s in data.series for v in s.values if v is not None]
    return nice_axis(min(values, default=0.0), max(values, default=0.0))


def visible_ticks(axis: Axis, cut: Break | None = None) -> list[float]:
    """The tick values to label; ticks inside an axis break's removed range are left out."""
    return [t for t in axis.ticks() if cut is None or not (cut.lower < t < cut.upper)]


def legend(names: Sequence[str], width: float) -> list[Primitive]:
    """A horizontal legend in the band ``0..LEGEND_HEIGHT`` across ``width``."""
    if not names:
        return []
    entry = width / len(names)
    top = (LEGEND_HEIGHT - SWATCH) / 2
    out: list[Primitive] = []
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
    stack then reaches above the chart, it moves down as a whole. Shared by the Mekko and the
    column layout.
    """
    spread_tops: list[float] = []
    for top in tops:
        spread_tops.append(min(top, spread_tops[-1] - height) if spread_tops else top)
    overshoot = min(spread_tops, default=0.0)
    return [top - min(overshoot, 0.0) for top in spread_tops]
