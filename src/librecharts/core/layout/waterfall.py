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

from librecharts.core import annotations as notes
from librecharts.core.axis_break import resolve_waterfall
from librecharts.core.layout.column import (
    BREAK_OVERHANG,
    LANE_HEIGHT,
    LANE_LINE_GAP,
    LEVEL_ARROW_INSET,
    LEVEL_LANE_WIDTH,
    bracket,
    break_mark,
    level_arrow,
)
from librecharts.core.layout.common import GAP_RATIO, format_value
from librecharts.core.model import Annotation
from librecharts.core.primitives import Line, Primitive, Rect, Text
from librecharts.core.scale import nice_axis
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
) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    measured = levels(data)
    brackets, level_arrows = notes.arrows(annotations, measured, "waterfall")
    lanes = len(brackets) * LANE_HEIGHT
    top_band = lanes + TOP_BAND
    plot_width = width - len(level_arrows) * LEVEL_LANE_WIDTH
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
    out: list[Primitive] = [Line(0, y(0), plot_width, y(0), "baseline")]

    for i, step in enumerate(data.steps):
        slot_x = i * slot
        x = slot_x + (slot - column_width) / 2
        top, bottom = y(max(step.start, step.end)), y(min(step.start, step.end))
        out.append(Rect(x, top, column_width, bottom - top, _series(step)))
        label_y = bottom if _label_below(step) else top - LABEL_HEIGHT
        out.append(Text(x, label_y, column_width, LABEL_HEIGHT, _label(step), "center", "value"))
        if i < len(data.steps) - 1:
            next_x = (i + 1) * slot + (slot - column_width) / 2
            out.append(Line(x + column_width, y(step.end), next_x, y(step.end), "connector"))
        out.append(
            Text(
                slot_x, top_band + plot_height, slot, CATEGORY_BAND, step.name, "center", "category"
            )
        )
        if cut and step.is_total and cut.cuts(step.end):
            out.extend(break_mark(x, column_width, y(cut.lower), BREAK_OVERHANG))

    def edges(category: int) -> tuple[float, float]:
        column_x = category * slot + (slot - column_width) / 2
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
        arrow_x = plot_width + lane * LEVEL_LANE_WIDTH + LEVEL_ARROW_INSET
        out.extend(
            level_arrow(level(arrow.start), level(arrow.end), arrow_x, notes.label(arrow, measured))
        )
    return tuple(out)


def _same(value: float) -> float:
    return value


def step_at(
    data: WaterfallData,
    width: float,
    annotations: tuple[Annotation, ...],
    x: float,
    y: float,
) -> tuple[int, int | None] | None:
    """The step (column) at chart point (x, y), or ``None``.

    Uses the geometry of :func:`layout_waterfall`: points in the arrow lanes or outside the box hit
    nothing, the labels above and below a column count as the column.
    """
    brackets, level_arrows = notes.arrows(annotations, levels(data), "waterfall")
    plot_width = width - len(level_arrows) * LEVEL_LANE_WIDTH
    if not data.steps or not 0 <= x < plot_width or y < len(brackets) * LANE_HEIGHT:
        return None
    return int(x // (plot_width / len(data.steps))), None


def _series(step: Step) -> int:
    if step.is_total:
        return SERIES_TOTAL
    return SERIES_INCREASE if step.change >= 0 else SERIES_DECREASE


def _label_below(step: Step) -> bool:
    return step.end < 0 if step.is_total else step.change < 0


def _label(step: Step) -> str:
    if step.is_total:
        return format_value(step.end)
    if not step.has_value:
        return ""
    text = format_value(step.change)
    return f"+{text}" if step.change > 0 else text
