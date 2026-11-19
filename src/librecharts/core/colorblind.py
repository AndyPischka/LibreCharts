"""Colour-blindness simulation of a scheme or a single colour (M30)."""

from __future__ import annotations

from typing import Literal

from librecharts.core.style import Scheme

Kind = Literal["deuteranopia", "protanopia", "tritanopia"]
_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "deuteranopia": (
        (0.625, 0.375, 0.0),
        (0.7, 0.3, 0.0),
        (0.0, 0.3, 0.7),
    ),
    "protanopia": (
        (0.567, 0.433, 0.0),
        (0.558, 0.442, 0.0),
        (0.0, 0.242, 0.758),
    ),
    "tritanopia": (
        (0.95, 0.05, 0.0),
        (0.0, 0.433, 0.567),
        (0.0, 0.475, 0.525),
    ),
}


def simulate(colour: int, kind: Kind) -> int:
    """``colour`` as it looks with ``kind``; unknown kinds raise ``ValueError``."""
    if kind not in _MATRICES:
        raise ValueError(f"unknown colour-blindness kind: {kind!r}")
    red, green, blue = ((colour >> shift) & 0xFF for shift in (16, 8, 0))
    rows = _MATRICES[kind]
    channels = [max(0, min(255, round(r * red + g * green + b * blue))) for r, g, b in rows]
    return (channels[0] << 16) | (channels[1] << 8) | channels[2]


def scheme(scheme_in: Scheme, kind: Kind) -> Scheme:
    """A copy of ``scheme_in`` with every colour simulated."""
    from dataclasses import replace

    return replace(
        scheme_in,
        name=f"{scheme_in.name} ({kind})",
        palette=tuple(simulate(colour, kind) for colour in scheme_in.palette),
        text=simulate(scheme_in.text, kind),
        line=simulate(scheme_in.line, kind),
        background=simulate(scheme_in.background, kind),
    )
