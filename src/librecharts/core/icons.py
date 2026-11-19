"""A small built-in icon set drawn from primitives (M26)."""

from __future__ import annotations

from librecharts.core.primitives import Line, Polygon, Polyline, Primitive, Rect

ICONS = (
    "arrow-right",
    "arrow-up",
    "target",
    "warning",
    "check",
    "cross",
    "idea",
    "person",
    "gear",
    "calendar",
    "money",
    "chart",
)


def primitives(name: str, width: float, height: float) -> tuple[Primitive, ...]:
    """Simple monochrome line art scaled to ``width`` x ``height``; unknown names raise."""
    if name not in ICONS:
        raise ValueError(f"unknown icon: {name!r}")
    side = min(width, height)
    left = (width - side) / 2
    top = (height - side) / 2

    def p(fx: float, fy: float) -> tuple[float, float]:
        return left + fx * side, top + fy * side

    def line(x1: float, y1: float, x2: float, y2: float) -> Line:
        return Line(*p(x1, y1), *p(x2, y2), "annotation")

    if name == "arrow-right":
        return (
            line(0.15, 0.5, 0.8, 0.5),
            Polyline((p(0.55, 0.25), p(0.8, 0.5), p(0.55, 0.75)), 0),
        )
    if name == "arrow-up":
        return (
            line(0.5, 0.85, 0.5, 0.2),
            Polyline((p(0.25, 0.45), p(0.5, 0.2), p(0.75, 0.45)), 0),
        )
    if name == "target":
        return (
            Polygon(tuple(_circle_points(*p(0.5, 0.5), 0.35 * side)), 0),
            Polygon(tuple(_circle_points(*p(0.5, 0.5), 0.18 * side)), 0),
        )
    if name == "warning":
        return (
            Polyline((p(0.5, 0.12), p(0.9, 0.85), p(0.1, 0.85), p(0.5, 0.12)), 0),
            line(0.5, 0.38, 0.5, 0.62),
            line(0.5, 0.72, 0.5, 0.76),
        )
    if name == "check":
        return (Polyline((p(0.15, 0.55), p(0.4, 0.8), p(0.85, 0.2)), 0),)
    if name == "cross":
        return (line(0.2, 0.2, 0.8, 0.8), line(0.8, 0.2, 0.2, 0.8))
    if name == "idea":
        return (
            Polygon(tuple(_circle_points(*p(0.5, 0.42), 0.28 * side)), 0),
            line(0.35, 0.82, 0.65, 0.82),
            line(0.4, 0.92, 0.6, 0.92),
        )
    if name == "person":
        return (
            Polygon(tuple(_circle_points(*p(0.5, 0.28), 0.16 * side)), 0),
            Polyline((p(0.2, 0.9), p(0.25, 0.62), p(0.75, 0.62), p(0.8, 0.9)), 0),
        )
    if name == "gear":
        return (
            Polygon(tuple(_gear_points(*p(0.5, 0.5), 0.38 * side, 0.22 * side)), 0),
            Polygon(tuple(_circle_points(*p(0.5, 0.5), 0.12 * side)), 0),
        )
    if name == "calendar":
        return (
            Rect(*p(0.1, 0.2), 0.8 * side, 0.7 * side, 0),
            line(0.1, 0.4, 0.9, 0.4),
            line(0.3, 0.1, 0.3, 0.25),
            line(0.7, 0.1, 0.7, 0.25),
        )
    if name == "money":
        return (
            Polygon(tuple(_circle_points(*p(0.5, 0.5), 0.38 * side)), 0),
            line(0.5, 0.22, 0.5, 0.78),
            line(0.35, 0.38, 0.62, 0.38),
            line(0.35, 0.62, 0.65, 0.62),
        )
    return (  # chart
        line(0.1, 0.9, 0.9, 0.9),
        line(0.1, 0.1, 0.1, 0.9),
        Polyline((p(0.25, 0.7), p(0.45, 0.45), p(0.62, 0.58), p(0.85, 0.25)), 0),
    )


def _circle_points(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    import math

    return [
        (cx + radius * math.cos(math.radians(angle)), cy + radius * math.sin(math.radians(angle)))
        for angle in range(0, 360, 12)
    ]


def _gear_points(cx: float, cy: float, outer: float, inner: float) -> list[tuple[float, float]]:
    import math

    points: list[tuple[float, float]] = []
    for index in range(16):
        radius = outer if index % 2 == 0 else inner
        angle = index * 22.5
        points.append(
            (
                cx + radius * math.cos(math.radians(angle)),
                cy + radius * math.sin(math.radians(angle)),
            )
        )
    return points
