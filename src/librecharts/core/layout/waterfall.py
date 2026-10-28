"""Layout of waterfall (bridge) charts.

Columns run left to right like in the column layout. Steps float between the running totals before
and after them, totals stand on the baseline, and a thin connector links the end of each column to
the start of the next. Increases, decreases and totals get different ``series`` indices (colours).
Labels sit outside: above a bar that ends in a rise, below a fall; steps are shown with their sign.

As in the other layouts the kinds and order of the primitives depend only on the data, never on
the size: per column a bar, a label, a connector (all but the last) and the category name.
"""

from __future__ import annotations

from librecharts.core.layout.common import GAP_RATIO, format_value
from librecharts.core.primitives import Line, Primitive, Rect, Text
from librecharts.core.scale import nice_axis
from librecharts.core.waterfall import Step, WaterfallData

TOP_BAND = 800.0  # room above the plot for labels of rising bars
LABEL_HEIGHT = 600.0
CATEGORY_BAND = 1000.0  # room below the plot for category names

SERIES_TOTAL, SERIES_INCREASE, SERIES_DECREASE = 0, 1, 2


def layout_waterfall(data: WaterfallData, width: float, height: float) -> tuple[Primitive, ...]:
    """Lay out ``data`` into a ``width`` x ``height`` box.

    Raises ``ValueError`` if the box leaves no room for the plot.
    """
    plot_height = height - TOP_BAND - CATEGORY_BAND
    # Labels of falling bars hang below them and must not run into the category names.
    scale_height = plot_height - (LABEL_HEIGHT if any(_label_below(s) for s in data.steps) else 0.0)
    if width <= 0 or scale_height <= 0:
        raise ValueError("chart area too small")
    if not data.steps:
        return ()

    levels = [0.0] + [level for s in data.steps for level in (s.start, s.end)]
    axis = nice_axis(min(levels), max(levels))
    span = axis.maximum - axis.minimum

    def y(value: float) -> float:
        return TOP_BAND + (axis.maximum - value) / span * scale_height

    slot = width / len(data.steps)
    column_width = slot * (1 - GAP_RATIO)
    out: list[Primitive] = [Line(0, y(0), width, y(0), "baseline")]

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
                slot_x, TOP_BAND + plot_height, slot, CATEGORY_BAND, step.name, "center", "category"
            )
        )
    return tuple(out)


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
