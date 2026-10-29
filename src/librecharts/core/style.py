"""Colours and contrast rules shared by the renderer and the layouts (ADR 0014).

The palette lives here, not in ``lo/render.py``: a layout can ask for the colour behind a label and
decide whether its text needs to be white. Pure Python, no UNO.
"""

from __future__ import annotations

# Series colours, indexed like ``ChartData.series``. M8 extends this to colour schemes.
PALETTE: tuple[int, ...] = (0x8FB4E3, 0x5E8AC7, 0xC9D8EE, 0xA6A6A6, 0xF4B183, 0xD9D9D9)

BLACK = 0x000000
WHITE = 0xFFFFFF
TEXT_COLOR = BLACK
CONTRAST_THRESHOLD = 0.5  # relative luminance below this gets white text


def series_color(series: int) -> int:
    """The fill colour of a series index (wraps around like the renderer does)."""
    return PALETTE[series % len(PALETTE)]


def text_color(fill: int) -> int:
    """``WHITE`` or ``BLACK`` for text on the RGB colour ``fill`` (WCAG relative luminance)."""
    return WHITE if luminance(fill) < CONTRAST_THRESHOLD else BLACK


def luminance(rgb: int) -> float:
    """Relative luminance of a 0xRRGGBB colour, as defined by WCAG 2."""
    red, green, blue = (linear((rgb >> shift) & 0xFF) for shift in (16, 8, 0))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def linear(channel: int) -> float:
    """sRGB channel (0..255) converted to linear light."""
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
