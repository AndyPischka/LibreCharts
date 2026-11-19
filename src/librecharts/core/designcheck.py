"""Corporate design check: compare the shapes of a presentation with a corporate design (ADR 0029).

The corporate design is the colour-scheme file of M8 (``core/style.py``) with optional check rules:
further allowed colours and fonts, and slide margins that every shape must stay inside. The adapter
(``lo/designcheck.py``) reads every slide into :class:`ShapeInfo` records; this module finds the
deviations and computes their fixes. Pure Python, no UNO.

Charts are checked as a whole: their shapes take colours and font from the document's scheme, so a
chart deviates exactly when the document's scheme differs from the corporate one, and the fix is to
switch the scheme (every chart is redrawn). A chart can still sit outside the margins.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Literal, cast

from librecharts.core import style
from librecharts.core.messages import text

Issue = Literal["scheme", "fill", "line", "font", "text_color", "position"]
ShapeKind = Literal["chart", "element", "shape"]

MM = 100  # 1/100 mm per millimetre
MAX_MARGIN_MM = 200.0
MAX_LISTED = 25  # findings named one by one in a report; the rest are counted


class DesignError(ValueError):
    """A corporate design file is malformed (the scheme or its check rules)."""


@dataclass(frozen=True, slots=True)
class Margins:
    """The distance every shape keeps from the slide edges, in 1/100 mm."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0


@dataclass(frozen=True, slots=True)
class Rules:
    """A corporate design: the scheme every chart uses and what other shapes may use.

    Allowed colours are the scheme's palette, text, line and background colours plus ``colors``;
    allowed fonts the scheme's font plus ``fonts``. ``margins`` is ``None`` when positions are not
    checked.
    """

    scheme: style.Scheme
    colors: tuple[int, ...] = ()
    fonts: tuple[str, ...] = ()
    margins: Margins | None = None

    @property
    def allowed_colors(self) -> tuple[int, ...]:
        scheme = self.scheme
        seen: dict[int, None] = {}
        for colour in (*scheme.palette, scheme.text, scheme.line, scheme.background, *self.colors):
            seen.setdefault(colour, None)
        return tuple(seen)

    @property
    def allowed_fonts(self) -> tuple[str, ...]:
        return (self.scheme.font_name, *(f for f in self.fonts if f != self.scheme.font_name))

    def font_allowed(self, name: str) -> bool:
        return name.strip().lower() in {font.lower() for font in self.allowed_fonts}


@dataclass(frozen=True, slots=True)
class ShapeInfo:
    """What the check needs to know about one shape on a slide.

    ``slide`` is 0-based, ``path`` the indices from the slide down to the shape (shapes inside a
    plain group have longer paths). ``fill`` and ``line`` are ``None`` when the shape has no solid
    fill or no visible line; ``fonts`` and ``text_colors`` are those of its text portions
    (automatic text colours are left out). Only top-level shapes carry a box: ``box`` is ``None``
    for the children of a group, which move with it.
    """

    slide: int
    path: tuple[int, ...]
    label: str
    kind: ShapeKind = "shape"
    box: tuple[int, int, int, int] | None = None  # x, y, width, height
    fill: int | None = None
    line: int | None = None
    fonts: tuple[str, ...] = ()
    text_colors: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Finding:
    """One deviation. ``slide`` and ``path`` are ``None`` for the document's scheme."""

    issue: Issue
    actual: str
    expected: str
    slide: int | None = None
    path: tuple[int, ...] | None = None
    label: str = ""


@dataclass(frozen=True, slots=True)
class Fix:
    """What to change on one shape. ``colors`` maps a deviating colour to its replacement (fill,
    line and text alike); ``fonts`` a deviating font to the corporate one; ``box`` is the new
    position and size of a top-level shape."""

    slide: int
    path: tuple[int, ...]
    colors: dict[int, int] = field(default_factory=lambda: cast("dict[int, int]", {}))
    fonts: dict[str, str] = field(default_factory=lambda: cast("dict[str, str]", {}))
    box: tuple[int, int, int, int] | None = None


@dataclass(frozen=True, slots=True)
class Result:
    """The findings of a check and the fixes that resolve them."""

    findings: tuple[Finding, ...]
    fixes: tuple[Fix, ...]
    scheme: style.Scheme | None  # the scheme to switch the document to, or None if it matches

    @property
    def clean(self) -> bool:
        return not self.findings


def check(
    shapes: list[ShapeInfo] | tuple[ShapeInfo, ...],
    rules: Rules,
    document_scheme: style.Scheme,
    slide_size: tuple[int, int],
) -> Result:
    """Every deviation of ``shapes`` and the document's scheme from ``rules``, with their fixes.

    ``slide_size`` is (width, height) in 1/100 mm. The document's scheme only counts when the
    presentation has a chart: without one it is never shown.
    """
    findings: list[Finding] = []
    fixes: list[Fix] = []
    has_chart = any(shape.kind == "chart" for shape in shapes)
    scheme_differs = has_chart and not same_scheme(document_scheme, rules.scheme)
    if scheme_differs:
        findings.append(Finding("scheme", document_scheme.name, rules.scheme.name))
    allowed = rules.allowed_colors
    for shape in shapes:
        shape_findings, fix = _check_shape(shape, rules, allowed, slide_size)
        findings += shape_findings
        if fix is not None:
            fixes.append(fix)
    return Result(tuple(findings), tuple(fixes), rules.scheme if scheme_differs else None)


def same_scheme(first: style.Scheme, second: style.Scheme) -> bool:
    """Whether two schemes look the same; the name does not matter."""
    return replace(first, name=second.name) == second


def _check_shape(
    shape: ShapeInfo,
    rules: Rules,
    allowed: tuple[int, ...],
    slide_size: tuple[int, int],
) -> tuple[list[Finding], Fix | None]:
    findings: list[Finding] = []
    colors: dict[int, int] = {}
    fonts: dict[str, str] = {}
    box = None

    def found(issue: Issue, actual: str, expected: str) -> None:
        findings.append(Finding(issue, actual, expected, shape.slide, shape.path, shape.label))

    if shape.kind == "shape":  # charts follow the scheme, elements have fixed colours
        for issue, colour in (("fill", shape.fill), ("line", shape.line)):
            if colour is not None and colour not in allowed:
                colors[colour] = nearest(colour, allowed)
                found(cast("Issue", issue), hex_color(colour), hex_color(colors[colour]))
        for colour in dict.fromkeys(shape.text_colors):
            if colour not in allowed:
                colors[colour] = nearest(colour, allowed)
                found("text_color", hex_color(colour), hex_color(colors[colour]))
        for font in dict.fromkeys(shape.fonts):
            if font.strip() and not rules.font_allowed(font):
                fonts[font] = rules.scheme.font_name
                found("font", font, rules.scheme.font_name)
    if rules.margins is not None and shape.box is not None:
        inside = fit_inside(shape.box, rules.margins, slide_size)
        if inside != shape.box:
            box = inside
            found("position", box_text(shape.box), box_text(inside))
    if not (colors or fonts or box):
        return findings, None
    return findings, Fix(shape.slide, shape.path, colors, fonts, box)


def fit_inside(
    box: tuple[int, int, int, int], margins: Margins, slide_size: tuple[int, int]
) -> tuple[int, int, int, int]:
    """``box`` moved, and shrunk if it is too large, into the slide area within ``margins``.

    A shrunk shape keeps its aspect ratio. A margin area of no size leaves the box as it is.
    """
    x, y, width, height = box
    area_x, area_y = margins.left, margins.top
    area_w = slide_size[0] - margins.left - margins.right
    area_h = slide_size[1] - margins.top - margins.bottom
    if area_w <= 0 or area_h <= 0:
        return box
    if width > area_w or height > area_h:
        factor = min(area_w / width if width else 1.0, area_h / height if height else 1.0)
        width, height = round(width * factor), round(height * factor)
    x = min(max(x, area_x), area_x + area_w - width)
    y = min(max(y, area_y), area_y + area_h - height)
    return x, y, width, height


def nearest(colour: int, allowed: tuple[int, ...]) -> int:
    """The allowed colour closest to ``colour`` (weighted RGB distance, "redmean")."""
    return min(allowed, key=lambda candidate: (_distance(colour, candidate), candidate))


def _distance(first: int, second: int) -> float:
    r1, g1, b1 = (first >> 16) & 0xFF, (first >> 8) & 0xFF, first & 0xFF
    r2, g2, b2 = (second >> 16) & 0xFF, (second >> 8) & 0xFF, second & 0xFF
    mean = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return (2 + mean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - mean) / 256) * db * db


def hex_color(colour: int) -> str:
    return f"#{colour:06X}"


def box_text(box: tuple[int, int, int, int]) -> str:
    """A box as the report shows it: ``x/y, width x height`` in centimetres."""
    x, y, width, height = (value / 1000 for value in box)
    return f"{x:.1f}/{y:.1f} cm, {width:.1f} x {height:.1f} cm"


# Corporate design files.


def rules_from_json(content: str) -> Rules:
    """The corporate design in a scheme file: the scheme plus its optional ``check`` object.

    ``check`` may hold ``colors`` (further allowed colours, integers like the palette), ``fonts``
    (further allowed font names) and ``margins_mm`` (``left``, ``top``, ``right``, ``bottom`` in
    millimetres). Raises ``DesignError`` for a malformed file.
    """
    try:
        scheme = style.scheme_from_json(content)
    except style.SchemeError as exc:
        raise DesignError(str(exc)) from exc
    raw = cast("dict[str, object]", json.loads(content))
    check_raw = raw.get("check", {})
    if not isinstance(check_raw, dict):
        raise DesignError("check must be a JSON object")
    rules = cast("dict[str, object]", check_raw)
    unknown = sorted(set(rules) - {"colors", "fonts", "margins_mm"})
    if unknown:
        raise DesignError(f"unknown check rule(s): {', '.join(unknown)}")
    return Rules(
        scheme=scheme,
        colors=_colors(rules.get("colors", [])),
        fonts=_fonts(rules.get("fonts", [])),
        margins=_margins(rules.get("margins_mm")),
    )


def rules_to_json(rules: Rules) -> str:
    """A corporate design file for ``rules``: the scheme JSON with a ``check`` object."""
    raw = cast("dict[str, object]", json.loads(style.scheme_to_json(rules.scheme)))
    check_raw: dict[str, object] = {}
    if rules.colors:
        check_raw["colors"] = list(rules.colors)
    if rules.fonts:
        check_raw["fonts"] = list(rules.fonts)
    if rules.margins is not None:
        margins = rules.margins
        check_raw["margins_mm"] = {
            "left": margins.left / MM,
            "top": margins.top / MM,
            "right": margins.right / MM,
            "bottom": margins.bottom / MM,
        }
    if check_raw:
        raw["check"] = check_raw
    return json.dumps(raw, separators=(",", ":"), ensure_ascii=False)


def _colors(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise DesignError("check.colors must be a list of colours")
    colours: list[int] = []
    for item in cast("list[object]", value):
        if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 0xFFFFFF:
            raise DesignError(f"check.colors holds an invalid colour: {item!r}")
        colours.append(item)
    return tuple(colours)


def _fonts(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DesignError("check.fonts must be a list of font names")
    fonts: list[str] = []
    for item in cast("list[object]", value):
        if not isinstance(item, str) or not item.strip() or len(item) > style.MAX_FONT_NAME:
            raise DesignError(f"check.fonts holds an invalid font name: {item!r}")
        fonts.append(item.strip())
    return tuple(fonts)


def _margins(value: object) -> Margins | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DesignError("check.margins_mm must be a JSON object")
    raw = cast("dict[str, object]", value)
    unknown = sorted(set(raw) - {"left", "top", "right", "bottom"})
    if unknown:
        raise DesignError(f"unknown margin(s): {', '.join(unknown)}")
    values: dict[str, int] = {}
    for side in ("left", "top", "right", "bottom"):
        number = raw.get(side, 0)
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise DesignError(f"check.margins_mm.{side} must be a number")
        if not 0 <= number <= MAX_MARGIN_MM:
            raise DesignError(f"check.margins_mm.{side} must be between 0 and {MAX_MARGIN_MM:g}")
        values[side] = round(number * MM)
    return Margins(**values)


# Reports.


def report(result: Result, locale: str, *, fixed: bool = False) -> str:
    """What to tell the user: no deviations, or each one (up to ``MAX_LISTED``) and their count.

    With ``fixed`` the report says the deviations were corrected.
    """
    if result.clean:
        return text("design_clean", locale)
    lines = [
        text(
            "design_fixed" if fixed else "design_found",
            locale,
            count=str(len(result.findings)),
        )
    ]
    for finding in result.findings[:MAX_LISTED]:
        lines.append("- " + describe(finding, locale))
    if len(result.findings) > MAX_LISTED:
        lines.append(text("design_more", locale, count=str(len(result.findings) - MAX_LISTED)))
    return "\n".join(lines)


def describe(finding: Finding, locale: str) -> str:
    """One finding as a line of the report, e.g. ``Slide 2, "Title": font Arial, not Calibri``."""
    detail = text(
        f"design_issue_{finding.issue}", locale, actual=finding.actual, expected=finding.expected
    )
    if finding.slide is None:
        return detail
    if finding.slide < 0:
        where = text("design_where_master", locale, index=str(-finding.slide), shape=finding.label)
    else:
        where = text("design_where", locale, slide=str(finding.slide + 1), shape=finding.label)
    return f"{where}: {detail}"
