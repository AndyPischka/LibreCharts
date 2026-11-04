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
from librecharts.core.layout.bar import (
    ANCHOR_GAP,
    AXIS_BAND_HEIGHT,
    BRACKET_INSET,
    BRACKET_LANE_WIDTH,
    LABEL_GAP,
    LABEL_WIDTH,
    LEFT_BAND,
    LEVEL_LANE_HEIGHT,
    RIGHT_BAND,
    TICK_WIDTH,
    bracket_lane,
    level_lane,
)
from librecharts.core.layout.bar import (
    LEVEL_ARROW_INSET as H_LEVEL_ARROW_INSET,
)
from librecharts.core.layout.bar import (
    LEVEL_LABEL_GAP as H_LEVEL_LABEL_GAP,
)
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
from librecharts.core.model import Annotation, Format, LabelKey
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
    length_per_unit: float | None = None,
    horizontal: bool = False,
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    With ``horizontal`` the steps run top to bottom and the values left to right, like the bar
    layout; with stacked steps (``step.segments``) every series row of the data sheet is drawn as
    its own floating segment of the column.

    ``length_per_unit`` (same-scale group, ADR 0017) draws one value unit as that many 1/100 mm and
    anchors the scale at the plot bottom; an axis break is then ignored.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    if horizontal:
        return _layout_horizontal(data, width, height, annotations, fmt, length_per_unit)
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
    scale_height = plot_height - (LABEL_HEIGHT if any(_falls(s) for s in data.steps) else 0.0)
    if plot_width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    if not data.steps:
        return ()

    cut = None if length_per_unit is not None else resolve_waterfall(annotations, data)
    fold = cut.fold if cut else _same
    shown = [fold(level) for level in [0.0, *_levels_of(data)]]
    axis = nice_axis(min(shown), max(shown))
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        if length_per_unit is not None:
            return top_band + scale_height - (value - axis.minimum) * length_per_unit
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
        if step.segments:  # stacked waterfall: one floating segment per series row
            for j, (s_start, s_end, has_value) in enumerate(step.segments):
                top, bottom = y(max(s_start, s_end)), y(min(s_start, s_end))
                out.append(
                    Rect(x, top, column_width, bottom - top, _segment_series(step, s_end - s_start))
                )
                label_y = bottom if s_end < s_start else top - LABEL_HEIGHT
                out.append(
                    Text(
                        x,
                        label_y,
                        column_width,
                        LABEL_HEIGHT,
                        _segment_label(step, s_start, s_end, has_value, fmt),
                        "center",
                        "value",
                        key=LabelKey("value", i, j),
                    )
                )
        else:
            top, bottom = y(max(step.start, step.end)), y(min(step.start, step.end))
            out.append(Rect(x, top, column_width, bottom - top, _series(step)))
            label_y = bottom if _label_below(step) else top - LABEL_HEIGHT
            out.append(
                Text(
                    x,
                    label_y,
                    column_width,
                    LABEL_HEIGHT,
                    _label(step, fmt),
                    "center",
                    "value",
                    key=LabelKey("value", i),
                )
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
        label = 0.0 if _falls(step) else LABEL_HEIGHT
        return (left + right) / 2, y(_top(step)) - label - LANE_LINE_GAP

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


def natural_length_per_unit(
    data: WaterfallData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...] = (),
    fmt: Format | None = None,
    horizontal: bool = False,
) -> float | None:
    """How many 1/100 mm one value unit gets when the chart is drawn alone at this size."""
    fmt = fmt or Format()
    brackets, _level_arrows = notes.arrows(annotations, levels(data), "waterfall")
    if horizontal:
        plot_left = LEFT_BAND + (LABEL_WIDTH if any(_falls(s) for s in data.steps) else 0.0)
        scale = width - plot_left - RIGHT_BAND - len(brackets) * BRACKET_LANE_WIDTH
    else:
        top_band = len(brackets) * LANE_HEIGHT + TOP_BAND
        plot_left = AXIS_BAND if fmt.axis else 0.0
        plot_height = height - top_band - CATEGORY_BAND
        scale = plot_height - (LABEL_HEIGHT if any(_falls(s) for s in data.steps) else 0.0)
    if scale <= 0 or not data.steps:
        return None
    cut = resolve_waterfall(annotations, data)
    fold = cut.fold if cut else _same
    shown = [fold(level) for level in [0.0, *_levels_of(data)]]
    axis = nice_axis(min(shown), max(shown))
    span = axis.maximum - axis.minimum
    if span <= 0:
        return None
    return scale / span


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
    horizontal: bool = False,
    height: float | None = None,
) -> tuple[int, int | None] | None:
    """The step (column) at chart point (x, y), or ``None``.

    Uses the geometry of :func:`layout_waterfall`: points in the arrow lanes or outside the box hit
    nothing, the labels above and below a column (right and left of a bar) count as the step.
    """
    fmt = fmt or Format()
    brackets, level_arrows = notes.arrows(annotations, levels(data), "waterfall")
    lines = notes.value_lines(annotations, levels(data), "waterfall")
    if horizontal:
        if height is None:
            return None
        plot_left = LEFT_BAND + (LABEL_WIDTH if any(_falls(s) for s in data.steps) else 0.0)
        plot_width = width - plot_left - RIGHT_BAND - len(brackets) * BRACKET_LANE_WIDTH
        plot_top = TOP_BAND
        plot_height = height - plot_top - (len(level_arrows) + len(lines)) * LEVEL_LANE_HEIGHT
        if (
            not data.steps
            or not plot_left <= x < plot_left + plot_width
            or not plot_top <= y < plot_top + plot_height
        ):
            return None
        return int((y - plot_top) // (plot_height / len(data.steps))), None
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


def _segment_series(step: Step, change: float) -> int:
    """The colour of one stacked segment: by its own change, or the total colour."""
    if step.is_total:
        return SERIES_TOTAL
    return SERIES_INCREASE if change >= 0 else SERIES_DECREASE


def _levels_of(data: WaterfallData) -> list[float]:
    """Every level the steps touch: the segment boundaries of stacked steps included."""
    out: list[float] = []
    for step in data.steps:
        out.extend((step.start, step.end))
        out.extend(v for segment in step.segments for v in (segment[0], segment[1]))
    return out


def _top(step: Step) -> float:
    """The highest level a step reaches (its own top, or its last segment's end when stacked)."""
    return max([step.start, step.end, *(s[1] for s in step.segments)])


def _falls(step: Step) -> bool:
    """Whether the step's label hangs below it (to the left of a horizontal bar)."""
    if step.is_total:
        return step.end < 0
    if step.segments:
        return any(end < start for start, end, _ in step.segments)
    return step.change < 0


def _label_below(step: Step) -> bool:
    return _falls(step)


def _segment_label(step: Step, start: float, end: float, has_value: bool, fmt: Format) -> str:
    """The label of one stacked segment: the total, or the segment's signed change."""
    if step.is_total:
        return format_value(end, fmt)
    if not has_value:
        return ""
    text = format_value(end - start, fmt)
    return f"+{text}" if end > start else text


def _label(step: Step, fmt: Format) -> str:
    if step.is_total:
        return format_value(step.end, fmt)
    if not step.has_value:
        return ""
    text = format_value(step.change, fmt)
    return f"+{text}" if step.change > 0 else text


def _layout_horizontal(
    data: WaterfallData,
    width: float,
    height: float,
    annotations: tuple[Annotation, ...],
    fmt: Format | None,
    length_per_unit: float | None,
) -> tuple[Primitive, ...]:
    """A waterfall chart on its side: steps top to bottom, values left to right, bar style.

    Bracket arrows run in lanes right of the outside labels, level arrows and value lines in lanes
    below the plot, the value axis (if shown) under them. Stacked steps draw one horizontal segment
    per series row, labels outside the floating end.
    """
    fmt = fmt or Format()
    measured = levels(data)
    brackets, level_arrows = notes.arrows(annotations, measured, "waterfall")
    lines = notes.value_lines(annotations, measured, "waterfall")
    has_fall = any(_falls(s) for s in data.steps)
    plot_left = LEFT_BAND + (LABEL_WIDTH if has_fall else 0.0)
    plot_top = TOP_BAND
    plot_width = width - plot_left - RIGHT_BAND - len(brackets) * BRACKET_LANE_WIDTH
    axis_band = AXIS_BAND_HEIGHT if fmt.axis else 0.0
    plot_height = (
        height - plot_top - axis_band - (len(level_arrows) + len(lines)) * LEVEL_LANE_HEIGHT
    )
    if plot_width <= 0 or plot_height <= 0:
        raise ValueError("chart area too small")
    if not data.steps:
        return ()

    cut = None if length_per_unit is not None else resolve_waterfall(annotations, data)
    fold = cut.fold if cut else _same
    shown = [fold(level) for level in [0.0, *_levels_of(data)]]
    axis = nice_axis(min(shown), max(shown))
    span = axis.maximum - axis.minimum

    def x(value: float) -> float:
        if length_per_unit is not None:
            return plot_left + (value - axis.minimum) * length_per_unit
        return plot_left + (fold(value) - axis.minimum) / span * plot_width

    slot = plot_height / len(data.steps)
    thickness = slot * (1 - GAP_RATIO)
    plot_bottom = plot_top + plot_height
    out: list[Primitive] = [Line(x(0), plot_top, x(0), plot_bottom, "baseline")]
    if fmt.axis:
        out.extend(_h_axis(axis, cut, x, plot_bottom, fmt))

    for i, step in enumerate(data.steps):
        slot_top = plot_top + i * slot
        bar_y = slot_top + (slot - thickness) / 2
        segments = step.segments or ((step.start, step.end, step.has_value),)
        for j, (s_start, s_end, has_value) in enumerate(segments):
            left, right = x(min(s_start, s_end)), x(max(s_start, s_end))
            out.append(
                Rect(left, bar_y, right - left, thickness, _segment_series(step, s_end - s_start))
            )
            label_y = bar_y + (thickness - LABEL_HEIGHT) / 2
            text = _segment_label(step, s_start, s_end, has_value, fmt)
            if s_end >= s_start:
                out.append(
                    Text(
                        right + LABEL_GAP,
                        label_y,
                        LABEL_WIDTH - LABEL_GAP,
                        LABEL_HEIGHT,
                        text,
                        "left",
                        "value",
                        key=LabelKey("value", i, j),
                    )
                )
            else:
                out.append(
                    Text(
                        left - LABEL_WIDTH,
                        label_y,
                        LABEL_WIDTH - LABEL_GAP,
                        LABEL_HEIGHT,
                        text,
                        "right",
                        "value",
                        key=LabelKey("value", i, j),
                    )
                )
        if i < len(data.steps) - 1:
            next_y = plot_top + (i + 1) * slot + (slot - thickness) / 2
            out.append(Line(x(step.end), bar_y + thickness, x(step.end), next_y, "connector"))
        out.append(Text(0, slot_top, LEFT_BAND - LABEL_GAP, slot, step.name, "right", "category"))
        if cut and step.is_total and cut.cuts(step.end):
            out.extend(_h_break_mark(x(cut.lower), bar_y, thickness, BREAK_OVERHANG))

    lane_start = plot_left + plot_width + RIGHT_BAND

    def anchor(category: int) -> tuple[float, float]:
        """Where a bracket arrow meets a step: right of its outside label, at mid-height."""
        bar_y = plot_top + category * slot + (slot - thickness) / 2
        return x(_top(data.steps[category])) + LABEL_WIDTH + ANCHOR_GAP, bar_y + thickness / 2

    def level(category: int) -> tuple[float, float]:
        """Where a level arrow's helper line starts: bottom edge, at the level the step ends."""
        bar_y = plot_top + category * slot + (slot - thickness) / 2
        return x(data.steps[category].end), bar_y + thickness

    for lane, arrow in enumerate(brackets):
        out.extend(
            bracket_lane(
                anchor(arrow.start),
                anchor(arrow.end),
                lane_start + lane * BRACKET_LANE_WIDTH + BRACKET_INSET,
                notes.label(arrow, measured),
            )
        )
    lane_top = plot_bottom + axis_band
    for lane, arrow in enumerate(level_arrows):
        out.extend(
            level_lane(
                level(arrow.start),
                level(arrow.end),
                lane_top + lane * LEVEL_LANE_HEIGHT + H_LEVEL_ARROW_INSET,
                notes.label(arrow, measured),
            )
        )
    for lane, annotation in enumerate(lines):
        resolved = value_line.resolved(annotation, measured)
        if resolved is None:
            continue
        line_x = x(fold(resolved))
        label_y = lane_top + (len(level_arrows) + lane) * LEVEL_LANE_HEIGHT + H_LEVEL_LABEL_GAP
        out.append(Line(line_x, plot_top, line_x, plot_bottom, "helper"))
        out.append(
            Text(
                line_x - TICK_WIDTH / 2,
                label_y,
                TICK_WIDTH,
                LABEL_HEIGHT,
                format_value(resolved, fmt),
                "center",
                "annotation",
            )
        )
    return tuple(out)


def _h_axis(
    axis: Axis, cut: Break | None, x: Callable[[float], float], plot_bottom: float, fmt: Format
) -> list[Primitive]:
    """The horizontal axis line and its tick labels below the plot."""
    out: list[Primitive] = [
        Line(x(axis.minimum), plot_bottom, x(axis.maximum), plot_bottom, "axis"),
    ]
    for tick in visible_ticks(axis, cut):
        left = x(cut.fold(tick) if cut else tick) - TICK_WIDTH / 2
        out.append(
            Text(
                left,
                plot_bottom + TICK_GAP,
                TICK_WIDTH,
                TICK_HEIGHT,
                format_value(tick, fmt),
                "center",
                "axis",
            )
        )
    return out


def _h_break_mark(x_break: float, y: float, thickness: float, overhang: float) -> list[Primitive]:
    """A white vertical gap across a bar at ``x_break`` with two parallel slanted lines."""
    left, top, bottom = x_break - BREAK_GAP / 2, y - overhang, y + thickness + overhang
    return [
        Rect(left, top, BREAK_GAP, bottom - top, BACKGROUND),
        Line(left, top, left + BREAK_SLANT, bottom, "annotation"),
        Line(left + BREAK_GAP - BREAK_SLANT, top, left + BREAK_GAP, bottom, "annotation"),
    ]
