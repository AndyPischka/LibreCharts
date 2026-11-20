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


def test_a_palette_entry_and_the_font_can_be_changed() -> None:
    changed = style.with_palette(style.DEFAULT, 0, 0x112233)
    assert changed.palette[0] == 0x112233
    with pytest.raises(ValueError, match="range"):
        style.with_palette(style.DEFAULT, 99, 0)
    with pytest.raises(ValueError, match="range"):
        style.with_palette(style.DEFAULT, 0, 0x1000000)
    font = style.with_font(style.DEFAULT, "Arial", 12)
    assert font.font_name == "Arial"
    assert font.font_size == 12


def test_a_simulated_scheme_keeps_its_palette_size() -> None:
    scheme = colorblind.scheme(style.DEFAULT, "deuteranopia")
    assert len(scheme.palette) == len(style.DEFAULT.palette)
    assert scheme.name.endswith("(deuteranopia)")
    assert scheme.palette != style.DEFAULT.palette
