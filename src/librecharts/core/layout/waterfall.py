"""Layout of waterfall (bridge) charts.

Columns run left to right like in the column layout. Steps float between the running totals before
and after them, totals stand on the baseline, and a thin connector links the end of each column to
the start of the next. Increases, decreases and totals get different ``series`` indices (colours).
Labels sit outside: above a bar that ends in a rise, below a fall; steps are shown with their sign.

As in the other layouts the kinds and order of the primitives depend only on the data, never on
the size: per column a bar, a label, a connector (all but the last) and the category name.

Annotations are the column layout's: bracket arrows in lanes above the plot, level arrows in lanes
right of it. An arrow measures the level a column ends at (``waterfall.levels``). An axis break
only removes a range below all steps (core/axis_break.py): totals reaching beyond it get a break
mark, the floating steps move down as a whole.
"""

from __future__ import annotations

from collections.abc import Callable

from librecharts.core import annotations as notes
from librecharts.core import value_line
from librecharts.core.axis_break import Break, resolve_waterfall
from librecharts.core.datasheet import ChartData
from librecharts.core.layout.column import (
    BREAK_GAP,
    BREAK_OVERHANG,
    BREAK_SLANT,
    LANE_HEIGHT,
    LANE_LINE_GAP,
    LEVEL_ARROW_INSET,
    LEVEL_LABEL_GAP,
    LEVEL_LANE_WIDTH,
    bracket,
    break_mark,
    level_arrow,
)
from librecharts.core.layout.common import (
    AXIS_BAND,
    GAP_RATIO,
    TICK_GAP,
    TICK_HEIGHT,
    format_value,
    visible_ticks,
)
from librecharts.core.model import Annotation, Format
from librecharts.core.primitives import BACKGROUND, Line, Primitive, Rect, Text
from librecharts.core.scale import Axis, nice_axis
from librecharts.core.waterfall import Step, WaterfallData, levels

TOP_BAND = 800.0  # room above the plot for labels of rising bars
LABEL_HEIGHT = 600.0
CATEGORY_BAND = 1000.0  # room below the plot for category names


SERIES_TOTAL, SERIES_INCREASE, SERIES_DECREASE = 0, 1, 2


def layout_waterfall(
    data: WaterfallData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    fmt = fmt or Format()
    measured = levels(data)
    brackets, level_arrows = notes.arrows(annotations, measured, "waterfall")
    lines = notes.value_lines(annotations, measured, "waterfall")
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes + TOP_BAND
    plot_left = AXIS_BAND if fmt.axis else 0.0
    plot_width = width - plot_left - (len(level_arrows) + len(lines)) * LEVEL_LANE_WIDTH
    plot_height = height - top_band - CATEGORY_BAND
    # Labels of falling bars hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if any(_label_below(s) for s in data.steps) else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    if not data.steps:
        return ()

    cut = resolve_waterfall(annotations, data)
    fold = cut.fold if cut else _same
    shown = [fold(level) for level in [0.0] + [v for s in data.steps for v in (s.start, s.end)]]
    axis = nice_axis(min(shown), max(shown))
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        return top_band + (axis.maximum - fold(value)) / span * scale_height

    slot = plot_width / len(data.steps)
    column_width = slot * (1 - GAP_RATIO)
    out: list[Primitive] = []
    out.append(Line(plot_left, y(0), plot_left + plot_width, y(0), "baseline"))
    if fmt.axis:
        if fmt.gridlines:
            out.extend(_grid(axis, cut, y, plot_left, plot_width))
        out.extend(_axis(axis, cut, y, plot_left, fmt))

    for i, step in enumerate(data.steps):
        slot_x = plot_left + i * slot
        x = slot_x + (slot - column_width) / 2
        top, bottom = y(max(step.start, step.end)), y(min(step.start, step.end))
        out.append(Rect(x, top, column_width, bottom - top, _series(step)))
        label_y = bottom if _label_below(step) else top - LABEL_HEIGHT
        out.append(
            Text(x, label_y, column_width, LABEL_HEIGHT, _label(step, fmt), "center", "value")
        )
        if i < len(data.steps) - 1:
            next_x = plot_left + (i + 1) * slot + (slot - column_width) / 2
            out.append(Line(x + column_width, y(step.end), next_x, y(step.end), "connector"))
        out.append(
            Text(
                slot_x, top_band + plot_height, slot, CATEGORY_BAND, step.name, "center", "category"
            )
        )
        if cut and step.is_total and cut.cuts(step.end):
            out.extend(break_mark(x, column_width, y(cut.lower), BREAK_OVERHANG))

    def edges(category: int) -> tuple[float, float]:
        column_x = plot_left + category * slot + (slot - column_width) / 2
        return column_x, column_x + column_width

    def anchor(category: int) -> tuple[float, float]:
        """Where a bracket arrow meets a column: top centre, above its label if that is above."""
        step = data.steps[category]
        left, right = edges(category)
        label = 0.0 if _label_below(step) else LABEL_HEIGHT
        return (left + right) / 2, y(max(step.start, step.end)) - label - LANE_LINE_GAP

    def level(category: int) -> tuple[float, float]:
        """Where a level arrow's helper line starts: right edge, at the level the column ends."""
        return edges(category)[1], y(data.steps[category].end)

    for lane, arrow in enumerate(brackets):
        line_y = lanes - lane * LANE_HEIGHT - LANE_LINE_GAP
        out.extend(
            bracket(anchor(arrow.start), anchor(arrow.end), line_y, notes.label(arrow, measured))
        )
    for lane, arrow in enumerate(level_arrows):
        arrow_x = plot_left + plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(level(arrow.start), level(arrow.end), arrow_x, notes.label(arrow, measured))
        )
    for lane, annotation in enumerate(lines):
        out.extend(
            _value_line(
                annotation,
                measured,
                y,
                fold,
                plot_left,
                plot_width,
                len(level_arrows) + lane,
                fmt,
            )
        )
    return tuple(out)


def _axis(
    axis: Axis, cut: Break | None, y: Callable[[float], float], plot_left: float, fmt: Format
) -> list[Primitive]:
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


def _grid(
    axis: Axis,
    cut: Break | None,
    y: Callable[[float], float],
    plot_left: float,
    plot_width: float,
) -> list[Primitive]:
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
    y: Callable[[float], float],
    fold: Callable[[float], float],
    plot_left: float,
    plot_width: float,
    lane: int,
    fmt: Format,
) -> list[Primitive]:
    level = value_line.resolved(annotation, data)
    if level is None:
        return []
    line_y = y(fold(level))
    label_x = plot_left + plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
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


def _same(value: float) -> float:
    return value


def step_at(
    data: WaterfallData,
    width: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
    fmt: Format | None = None,
) -> tuple[int, int | None] | None:
    """The step (column) at chart point (x, y), or ``None``.

    Uses the geometry of :func:`layout_waterfall`: points in the arrow lanes or outside the box hit
    nothing, the labels above and below a column count as the column.
    """
    fmt = fmt or Format()
    brackets, level_arrows = notes.arrows(annotations, levels(data), "waterfall")
    lines = notes.value_lines(annotations, levels(data), "waterfall")
    plot_left = AXIS_BAND if fmt.axis else 0.0
    plot_width = width - plot_left - (len(level_arrows) + len(lines)) * LEVEL_LANE_WIDTH
    if (
        not data.steps
        or not plot_left <= x < plot_left + plot_width
        or y < len(brackets) * LANE_HEIGHT
    ):
        return None
    return int((x - plot_left) // (plot_width / len(data.steps))), None


def _series(step: Step) -> int:
    if step.is_total:
        return SERIES_TOTAL
    return SERIES_INCREASE if step.change >= 0 else SERIES_DECREASE


def _label_below(step: Step) -> bool:
    return step.end < 0 if step.is_total else step.change < 0


def _label(step: Step, fmt: Format) -> str:
    if step.is_total:
        return format_value(step.end, fmt)
    if not step.has_value:
        return ""
    text = format_value(step.change, fmt)
    return f"+{text}" if step.change > 0 else text
