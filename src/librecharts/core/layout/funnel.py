"""Funnel charts: centred horizontal bars in stage order (M24)."""

from __future__ import annotations

from librecharts.core.datasheet import ChartData
from librecharts.core.layout.common import LABEL_HEIGHT, format_value
from librecharts.core.model import Format
from librecharts.core.primitives import Primitive, Rect, Text

TOP_BAND = 600.0
CATEGORY_BAND = 800.0
LABEL_WIDTH = 1800.0
MIN_HEIGHT = 250.0


def layout_funnel(
    data: ChartData, width: float, height: float, fmt: Format | None = None
) -> tuple[Primitive, ...]:
    """Stages as centred bars, widest at the top; a value and conversion label per stage."""
    fmt = fmt or Format()
    if not data.categories or not data.series:
        return ()
    values = [value or 0.0 for value in data.series[0].values]
    highest = max(values)
    if highest <= 0:
        return ()
    plot_height = height - TOP_BAND - CATEGORY_BAND
    if plot_height <= 0:
        raise ValueError("chart area too small")
    slot = plot_height / len(values)
    out: list[Primitive] = []
    for index, category in enumerate(data.categories):
        value = values[index]
        centre = TOP_BAND + (index + 0.5) * slot
        bar_height = max(slot * 0.7, MIN_HEIGHT)
        bar_width = max(width * value / highest, 200.0)
        left = (width - bar_width) / 2
        out.append(Rect(left, centre - bar_height / 2, bar_width, bar_height, 0, category=index))
        detail = format_value(value, fmt)
        if index and values[index - 1] > 0:
            detail += f"  ({value / values[index - 1] * 100:.1f} %)"
        out.append(
            Text(
                left,
                centre - LABEL_HEIGHT / 2,
                bar_width,
                LABEL_HEIGHT,
                detail,
                "center",
                "value",
            )
        )
        out.append(
            Text(
                0,
                centre - LABEL_HEIGHT / 2,
                left - 100,
                LABEL_HEIGHT,
                category,
                "right",
                "category",
            )
        )
    return tuple(out)
