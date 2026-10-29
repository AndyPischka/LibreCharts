import pytest

from librecharts.core import elements
from librecharts.core.elements import Element
from librecharts.core.primitives import NEGATIVE, POSITIVE, Polygon, Polyline


@pytest.mark.parametrize(
    "element",
    [Element.harvey(level) for level in elements.HARVEY_LEVELS]
    + [Element.check(symbol) for symbol in elements.CHECK_SYMBOLS],
)
def test_names_round_trip_and_end_in_a_non_digit(element: Element) -> None:
    group_name = elements.name(element)
    assert elements.parse(group_name) == element
    assert not group_name[-1].isdigit()  # LibreOffice cuts trailing digits off a copy's name


def test_the_name_of_a_copy_is_still_recognised() -> None:
    assert elements.parse("librecharts-element:harvey:50% 1") == Element.harvey(50)
    assert elements.parse("librecharts-element:check:tick 12") == Element.check("tick")


@pytest.mark.parametrize(
    "group_name",
    ["", "librecharts:abc", "librecharts-element:harvey:30%", "librecharts-element:check:", "x"],
)
def test_other_names_are_no_elements(group_name: str) -> None:
    assert elements.parse(group_name) is None


def test_invalid_states_are_rejected() -> None:
    with pytest.raises(ValueError, match=r"a Harvey|a check|unknown"):
        Element.harvey(30)
    with pytest.raises(ValueError, match=r"a Harvey|a check|unknown"):
        Element.check("star")


def test_following_cycles_through_all_states() -> None:
    ball = Element.harvey(0)
    seen = [ball]
    for _ in range(5):
        ball = elements.following(ball)
        seen.append(ball)
    assert [e.value for e in seen] == ["0", "25", "50", "75", "100", "0"]
    assert elements.following(Element.check("empty")) == Element.check("tick")


def test_query_parsing() -> None:
    assert elements.parse_query("harvey=75") == Element.harvey(75)
    assert elements.parse_query("check=cross") == Element.check("cross")
    for bad in ("", "harvey=x", "harvey=30", "check=star", "other=1"):
        with pytest.raises(ValueError, match=r"a Harvey|a check|unknown"):
            elements.parse_query(bad)


def test_a_harvey_ball_is_an_outline_plus_a_sector_except_when_empty() -> None:
    empty = elements.layout_element(Element.harvey(0), 600, 600)
    half = elements.layout_element(Element.harvey(50), 600, 600)
    assert len(empty) == 1
    assert len(half) == 2
    assert isinstance(half[0], Polygon)
    assert half[0].outline
    assert isinstance(half[1], Polygon)
    assert not half[1].outline


def test_the_structure_does_not_depend_on_the_size() -> None:
    for element in (Element.harvey(25), Element.check("tick"), Element.check("cross")):
        small = elements.layout_element(element, 300, 300)
        large = elements.layout_element(element, 900, 500)
        assert [type(p) for p in small] == [type(p) for p in large]
        assert [len(getattr(p, "points", ())) for p in small] == [
            len(getattr(p, "points", ())) for p in large
        ]


def test_the_element_is_a_centred_square_in_a_wide_box() -> None:
    (circle,) = elements.layout_element(Element.check("empty"), 1000, 400)
    assert isinstance(circle, Polygon)
    xs = [x for x, _ in circle.points]
    ys = [y for _, y in circle.points]
    assert max(ys) - min(ys) == pytest.approx(400, abs=1)
    assert (max(xs) + min(xs)) / 2 == pytest.approx(500, abs=1)


def test_tick_and_cross_use_their_fixed_colours() -> None:
    (tick,) = elements.layout_element(Element.check("tick"), 600, 600)
    cross = elements.layout_element(Element.check("cross"), 600, 600)
    assert isinstance(tick, Polyline)
    assert tick.series == POSITIVE
    assert [p.series for p in cross if isinstance(p, Polyline)] == [NEGATIVE, NEGATIVE]
