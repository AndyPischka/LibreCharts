"""Colour schemes and contrast rules shared by the renderer and the layouts (ADRs 0014, 0016).

A scheme is the document-wide look: the series palette, text and line colours, the background behind
axis-break gaps and the font. The built-in schemes are plain data, so the adapter can offer them and
a corporate design can be loaded from the same JSON format. Pure Python, no UNO.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

# Series colours of the default scheme, indexed like ``ChartData.series``.
PALETTE: tuple[int, ...] = (0x8FB4E3, 0x5E8AC7, 0xC9D8EE, 0xA6A6A6, 0xF4B183, 0xD9D9D9)

BLACK = 0x000000
WHITE = 0xFFFFFF
TEXT_COLOR = BLACK
LINE_COLOR = 0x404040
CONTRAST_THRESHOLD = 0.5  # relative luminance below this gets white text

SCHEME_VERSION = 1
MAX_PALETTE = 32
MAX_FONT_NAME = 64


@dataclass(frozen=True, slots=True)
class Scheme:
    """The colours and font of every chart in one document (ADR 0016).

    ``palette`` holds the series colours; a series index wraps around it. ``text`` is the colour of
    labels on the background, ``line`` the colour of axes, connectors and annotation lines, and
    ``background`` the colour of the gaps of axis breaks (which cover shapes behind them). Text on a
    filled segment uses :func:`text_color` instead, so it stays readable on every palette colour.
    ``colors`` of a chart can point a single series at another entry of ``palette``.
    """

    name: str
    palette: tuple[int, ...]
    text: int = TEXT_COLOR
    line: int = LINE_COLOR
    background: int = WHITE
    font_name: str = "Liberation Sans"
    font_size: float = 10.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a colour scheme needs a name")
        if not self.palette:
            raise ValueError("a colour scheme needs at least one colour")
        if len(self.palette) > MAX_PALETTE:
            raise ValueError(f"a colour scheme has at most {MAX_PALETTE} colours")
        for colour in (*self.palette, self.text, self.line, self.background):
            if isinstance(colour, bool) or not 0 <= colour <= 0xFFFFFF:
                raise ValueError(f"colour out of range: {colour!r}")
        if not self.font_name.strip() or len(self.font_name) > MAX_FONT_NAME:
            raise ValueError("the font name must be 1 to 64 characters long")
        if not 4.0 <= self.font_size <= 72.0:
            raise ValueError("the font size must be between 4 and 72 points")

    def color(self, series: int, overrides: tuple[int | None, ...] = ()) -> int:
        """The fill colour of a series, honouring a chart's per-series palette indices."""
        if 0 <= series < len(overrides) and (override := overrides[series]) is not None:
            return self.palette[override % len(self.palette)]
        return self.palette[series % len(self.palette)]

    def grid(self) -> int:
        """A light colour for gridlines: the line colour mixed far towards the background."""
        return mix(self.line, self.background, 0.15)

    def shade(self) -> int:
        """A very light colour for bands behind the data: a little line colour in the background."""
        return mix(self.background, self.line, 0.08)

    def text_on(self, fill: int) -> int:
        """A readable text colour on ``fill`` (WCAG relative luminance)."""
        return text_color(fill)


DEFAULT = Scheme("Default", PALETTE)
GREY = Scheme(
    "Grey",
    (0xD9D9D9, 0xA6A6A6, 0x808080, 0xBFBFBF, 0x595959, 0xEDEDED),
)
HIGH_CONTRAST = Scheme(
    "High contrast",
    (0x1F4E79, 0xE69F00, 0xC00000, 0x007A33, 0x6A3D9A, 0x00A3D9),
    text=BLACK,
    line=BLACK,
)

BUILT_INS: tuple[Scheme, ...] = (DEFAULT, GREY, HIGH_CONTRAST)


def series_color(series: int) -> int:
    """The fill colour of a series index in the default scheme (wraps around)."""
    return DEFAULT.color(series)


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


def mix(first: int, second: int, share: float) -> int:
    """``share`` of ``second`` mixed into ``first``."""
    channels = [
        round(((first >> shift) & 0xFF) * (1 - share) + ((second >> shift) & 0xFF) * share)
        for shift in (16, 8, 0)
    ]
    return (channels[0] << 16) | (channels[1] << 8) | channels[2]


def built_in(name: str) -> Scheme | None:
    """The built-in scheme called ``name`` (case-insensitive), or ``None``."""
    wanted = name.strip().lower()
    return next((scheme for scheme in BUILT_INS if scheme.name.lower() == wanted), None)


class SchemeError(ValueError):
    """A colour scheme file is malformed or from an unsupported version."""


def scheme_to_json(scheme: Scheme) -> str:
    """Serialize ``scheme`` for a document property or a corporate-design file."""
    return json.dumps(
        {
            "v": SCHEME_VERSION,
            "name": scheme.name,
            "palette": list(scheme.palette),
            "text": scheme.text,
            "line": scheme.line,
            "background": scheme.background,
            "font_name": scheme.font_name,
            "font_size": scheme.font_size,
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def scheme_from_json(text: str) -> Scheme:
    """Parse a scheme written by :func:`scheme_to_json`.

    Raises ``SchemeError`` for invalid JSON, an unsupported version or a field that is not a valid
    colour, font or palette. Missing optional fields fall back to the defaults, so a short corporate
    design file only needs its palette.
    """
    try:
        raw: object = json.loads(text, parse_constant=_reject_constant)
    except ValueError as exc:
        raise SchemeError(f"invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SchemeError("a colour scheme must be a JSON object")
    data = cast("dict[str, object]", raw)
    version = data.get("v", SCHEME_VERSION)
    if isinstance(version, bool) or not isinstance(version, int):
        raise SchemeError("missing or invalid scheme version 'v'")
    if version > SCHEME_VERSION:
        raise SchemeError(
            f"colour scheme saved by a newer LibreCharts (version {version}, "
            f"supported {SCHEME_VERSION})"
        )
    if version < 1:
        raise SchemeError(f"unsupported colour scheme version {version}")
    try:
        return Scheme(
            name=_string(data.get("name", "Imported"), "name"),
            palette=_palette(data.get("palette")),
            text=_colour(data.get("text", TEXT_COLOR), "text"),
            line=_colour(data.get("line", LINE_COLOR), "line"),
            background=_colour(data.get("background", WHITE), "background"),
            font_name=_string(data.get("font_name", "Liberation Sans"), "font_name"),
            font_size=_number(data.get("font_size", 10.0)),
        )
    except ValueError as exc:
        raise SchemeError(str(exc)) from exc


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not valid JSON")


def _palette(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise SchemeError("the palette must be a list of colours")
    return tuple(_colour(item, "palette") for item in cast("list[object]", value))


def _colour(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemeError(f"{name} must be an integer colour")
    if not 0 <= value <= 0xFFFFFF:
        raise SchemeError(f"{name} is out of range: {value!r}")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise SchemeError(f"{name} must be a string")
    return value


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemeError("font_size must be a number")
    return float(value)
