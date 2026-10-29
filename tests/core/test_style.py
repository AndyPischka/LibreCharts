import json

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


def test_a_scheme_wraps_its_palette_and_honours_overrides() -> None:
    scheme = style.Scheme("Test", (0x111111, 0x222222))
    assert scheme.color(0) == 0x111111
    assert scheme.color(2) == 0x111111
    assert scheme.color(0, (1,)) == 0x222222
    assert scheme.color(0, (None,)) == 0x111111
    assert scheme.color(0, (4,)) == 0x111111  # wraps like the default palette


def test_gridlines_mix_the_line_colour_towards_the_background() -> None:
    scheme = style.Scheme("Test", (0x111111,), line=0x000000, background=0xFFFFFF)
    assert style.luminance(scheme.grid()) > style.luminance(scheme.line)
    assert scheme.text_on(0x000000) == style.WHITE


@pytest.mark.parametrize(
    "scheme",
    [
        {"name": " ", "palette": (0x111111,)},
        {"name": "Test", "palette": ()},
        {"name": "Test", "palette": (0x1000000,)},
        {"name": "Test", "palette": (True,)},
        {"name": "Test", "palette": (0x111111,), "font_name": ""},
        {"name": "Test", "palette": (0x111111,), "font_size": 2.0},
        {"name": "Test", "palette": (0x111111,), "font_size": 100.0},
    ],
)
def test_a_scheme_rejects_invalid_fields(scheme: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"colour|font|name"):
        style.Scheme(**scheme)  # pyright: ignore[reportArgumentType]


def test_built_in_schemes_are_found_case_insensitively() -> None:
    assert style.built_in("default") is style.DEFAULT
    assert style.built_in("GREY") is style.GREY
    assert style.built_in("High Contrast") is style.HIGH_CONTRAST
    assert style.built_in("missing") is None


def test_a_scheme_round_trips_through_json() -> None:
    scheme = style.Scheme(
        "Corporate",
        (0x112233, 0x445566),
        text=0x010203,
        line=0x040506,
        background=0xF0F0F0,
        font_name="Arial",
        font_size=12.5,
    )
    assert style.scheme_from_json(style.scheme_to_json(scheme)) == scheme


def test_a_short_scheme_file_only_needs_a_palette() -> None:
    loaded = style.scheme_from_json(json.dumps({"palette": [0x112233]}))
    assert loaded.name == "Imported"
    assert loaded.palette == (0x112233,)
    assert loaded.text == style.TEXT_COLOR
    assert loaded.font_size == 10.0


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"palette": [1], "v": 99}',
        '{"palette": [1], "v": 0}',
        '{"palette": "red"}',
        '{"palette": [1], "text": true}',
        '{"palette": [1], "text": 99999999}',
        '{"palette": [1], "name": 3}',
        '{"palette": [1], "font_size": "big"}',
        '{"palette": [NaN]}',
    ],
)
def test_invalid_scheme_files_raise_a_scheme_error(text: str) -> None:
    with pytest.raises(style.SchemeError):
        style.scheme_from_json(text)


def test_a_newer_scheme_file_is_rejected_with_a_clear_message() -> None:
    with pytest.raises(style.SchemeError, match="newer LibreCharts"):
        style.scheme_from_json('{"palette": [1], "v": 2}')
