from datetime import date, timedelta

import pytest

from librecharts.core.timescale import (
    MAX_UNITS,
    Period,
    after,
    floor,
    format_date,
    label,
    time_scale,
)


@pytest.mark.parametrize(
    ("days", "pair"),
    [
        (1, ("day", "month")),
        (40, ("day", "month")),
        (41, ("week", "month")),
        (200, ("week", "month")),
        (300, ("month", "year")),
        (3 * 365, ("month", "year")),
        (4 * 365, ("quarter", "year")),
        (10 * 365, ("quarter", "year")),
        (12 * 365, ("year", "decade")),
        (300 * 365, ("year", "decade")),
    ],
)
def test_the_unit_pair_follows_the_length_of_the_range(days: int, pair: tuple[str, str]) -> None:
    first = date(2026, 1, 1)
    scale = time_scale(first, first + timedelta(days=days - 1))
    assert (scale.lower, scale.upper) == pair


@pytest.mark.parametrize("days", [1, 7, 39, 41, 100, 500, 1500, 3000])
def test_the_lower_level_has_at_most_forty_units_below_a_decade(days: int) -> None:
    first = date(2026, 3, 17)
    scale = time_scale(first, first + timedelta(days=days))
    assert 1 <= len(scale.periods(scale.lower)) <= MAX_UNITS


def test_the_scale_snaps_to_whole_lower_units() -> None:
    scale = time_scale(date(2026, 1, 7), date(2026, 5, 20))  # a Wednesday to a Wednesday
    assert scale.lower == "week"
    assert scale.start == date(2026, 1, 5)  # Monday
    assert scale.end == date(2026, 5, 25)  # the Monday after the last week
    assert scale.fraction(scale.start) == 0
    assert scale.fraction(scale.end) == 1


def test_upper_periods_are_clipped_to_the_scale() -> None:
    scale = time_scale(date(2026, 1, 7), date(2026, 3, 3))
    upper = scale.periods(scale.upper)
    assert upper[0] == Period(date(2026, 1, 5), date(2026, 2, 1))
    assert upper[-1] == Period(date(2026, 3, 1), scale.end)
    assert scale.labelled(upper[0], "month")
    assert not scale.labelled(upper[-1], "month")  # only a week of March


@pytest.mark.parametrize(
    ("unit", "day", "start", "following"),
    [
        ("day", date(2026, 2, 28), date(2026, 2, 28), date(2026, 3, 1)),
        ("week", date(2026, 3, 1), date(2026, 2, 23), date(2026, 3, 2)),
        ("month", date(2026, 12, 15), date(2026, 12, 1), date(2027, 1, 1)),
        ("quarter", date(2026, 8, 31), date(2026, 7, 1), date(2026, 10, 1)),
        ("year", date(2026, 8, 31), date(2026, 1, 1), date(2027, 1, 1)),
        ("decade", date(2026, 8, 31), date(2020, 1, 1), date(2030, 1, 1)),
    ],
)
def test_units_start_and_end_on_calendar_boundaries(
    unit: str, day: date, start: date, following: date
) -> None:
    assert floor(day, unit) == start  # pyright: ignore[reportArgumentType]
    assert after(start, unit) == following  # pyright: ignore[reportArgumentType]


def test_the_scale_counts_calendar_years() -> None:
    assert time_scale(date(2026, 1, 1), date(2026, 12, 31)).years == 1
    assert time_scale(date(2026, 11, 1), date(2027, 2, 1)).years == 2


@pytest.mark.parametrize(
    ("unit", "upper", "language", "expected"),
    [
        ("day", False, "en", "5"),
        ("week", False, "de", "10"),  # ISO week of 2026-03-05
        ("month", False, "en", "Mar"),
        ("month", False, "de", "Mär"),
        ("month", True, "en", "Mar 2026"),
        ("month", True, "de", "Mär 2026"),
        ("quarter", False, "de", "Q1"),
        ("year", True, "en", "2026"),
        ("decade", True, "en", "2020s"),
        ("decade", True, "de", "2020er"),
    ],
)
def test_labels_in_english_and_german(unit: str, upper: bool, language: str, expected: str) -> None:
    assert label(date(2026, 3, 5), unit, language, upper=upper) == expected  # pyright: ignore[reportArgumentType]


def test_dates_are_formatted_per_language() -> None:
    day = date(2026, 6, 30)
    assert format_date(day, "de") == "30.06.2026"
    assert format_date(day, "de", with_year=False) == "30.06."
    assert format_date(day, "en") == "30 Jun 2026"
    assert format_date(day, "en", with_year=False) == "30 Jun"
    assert format_date(day, "fr") == "30 Jun 2026"  # unknown languages fall back to English
