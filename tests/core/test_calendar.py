from datetime import date, timedelta

import pytest

from librecharts.core.calendar import active, changed, check_holidays, is_working, working_between
from librecharts.core.model import Calendar

MONDAY = date(2026, 3, 2)  # a Monday
WEEKDAYS = Calendar((0, 1, 2, 3, 4))


def test_the_default_calendar_has_every_day_working() -> None:
    assert Calendar().working_days == (0, 1, 2, 3, 4, 5, 6)
    assert not active(Calendar())
    assert is_working(Calendar(), date(2026, 3, 7))  # a Saturday


def test_weekends_are_not_working_days() -> None:
    assert is_working(WEEKDAYS, MONDAY)
    assert not is_working(WEEKDAYS, date(2026, 3, 7))  # Saturday
    assert not is_working(WEEKDAYS, date(2026, 3, 8))  # Sunday
    assert active(WEEKDAYS)


def test_a_holiday_is_not_working_even_on_a_weekday() -> None:
    calendar = Calendar(holidays=(date(2026, 3, 3),))
    assert not is_working(calendar, date(2026, 3, 3))
    assert active(calendar)


def test_working_between_counts_whole_weeks_and_remainders() -> None:
    assert working_between(WEEKDAYS, MONDAY, MONDAY) == 0
    assert working_between(WEEKDAYS, MONDAY, MONDAY + timedelta(days=1)) == 1
    assert working_between(WEEKDAYS, MONDAY, MONDAY + timedelta(days=7)) == 5
    assert working_between(WEEKDAYS, MONDAY, MONDAY + timedelta(days=14)) == 10
    friday = date(2026, 3, 6)
    assert working_between(WEEKDAYS, friday, friday + timedelta(days=3)) == 1


def test_working_between_subtracts_holidays_only_on_working_weekdays() -> None:
    calendar = Calendar((0, 1, 2, 3, 4), (date(2026, 3, 3), date(2026, 3, 7)))
    # Tuesday is a holiday; Saturday already is not a working day.
    assert working_between(calendar, MONDAY, MONDAY + timedelta(days=7)) == 4


def test_working_between_handles_a_range_that_ends_before_it_starts() -> None:
    assert working_between(WEEKDAYS, MONDAY, MONDAY - timedelta(days=1)) == 0


def test_holidays_are_parsed_in_the_chart_language() -> None:
    assert check_holidays("2026-12-25\n25.12.2026; 2026-12-25", "de") == (date(2026, 12, 25),)
    assert check_holidays("12/25/2026", "en") == (date(2026, 12, 25),)
    assert check_holidays("25/12/2026", "de") == (date(2026, 12, 25),)


def test_an_invalid_holiday_is_an_error_key() -> None:
    assert check_holidays("soon", "en") == "working_days_bad_date"
    assert check_holidays("2026-02-30", "en") == "working_days_bad_date"


def test_the_query_sets_working_days_and_holidays() -> None:
    calendar = changed(Calendar(), "working=1,2,3,4,5&holidays=2026-12-25", "en")
    assert calendar == Calendar((0, 1, 2, 3, 4), (date(2026, 12, 25),))


def test_a_missing_query_field_keeps_the_current_value() -> None:
    current = Calendar((0, 1, 2, 3, 4), (date(2026, 12, 25),))
    assert changed(current, "working=1,2,3,4,5,6,7", "en") == Calendar(
        (0, 1, 2, 3, 4, 5, 6), (date(2026, 12, 25),)
    )
    assert changed(current, "holidays=", "en") == Calendar((0, 1, 2, 3, 4), ())


@pytest.mark.parametrize(
    "query",
    ["working=0", "working=8", "working=x", "working=", "unknown=1", "holidays=soon"],
)
def test_an_invalid_query_raises(query: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        changed(Calendar(), query, "en")
