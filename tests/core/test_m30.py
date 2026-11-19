"""M30: colour-blindness simulation and element descriptions."""

from __future__ import annotations

import pytest

from librecharts.core import colorblind, style


def test_every_simulation_keeps_channels_in_range() -> None:
    for kind in ("deuteranopia", "protanopia", "tritanopia"):
        for colour in style.PALETTE:
            simulated = colorblind.simulate(colour, kind)  # pyright: ignore[reportArgumentType]
            assert 0 <= simulated <= 0xFFFFFF
    with pytest.raises(ValueError, match="colour-blindness"):
        colorblind.simulate(0x123456, "nope")  # pyright: ignore[reportArgumentType]


def test_a_simulated_scheme_keeps_its_palette_size() -> None:
    scheme = colorblind.scheme(style.DEFAULT, "deuteranopia")
    assert len(scheme.palette) == len(style.DEFAULT.palette)
    assert scheme.name.endswith("(deuteranopia)")
    assert scheme.palette != style.DEFAULT.palette
