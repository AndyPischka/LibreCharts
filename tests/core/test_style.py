import pytest

from librecharts.core import style


@pytest.mark.parametrize(
    ("rgb", "expected"),
    [
        (style.BLACK, 0.0),
        (style.WHITE, 1.0),
        (0x808080, 0.2159),
    ],
)
def test_relative_luminance(rgb: int, expected: float) -> None:
    assert style.luminance(rgb) == pytest.approx(expected, abs=1e-4)


def test_dark_fills_get_white_text() -> None:
    assert style.text_color(style.BLACK) == style.WHITE
    assert style.text_color(0x003366) == style.WHITE
    assert style.text_color(style.WHITE) == style.BLACK
    assert style.text_color(0xC9D8EE) == style.BLACK


def test_the_palette_wraps_around() -> None:
    assert style.series_color(0) == style.PALETTE[0]
    assert style.series_color(len(style.PALETTE)) == style.PALETTE[0]
    assert style.series_color(-1) == style.PALETTE[-1]
