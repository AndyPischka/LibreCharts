"""Working-day calendars for Gantt charts (M17): weekends, holidays and their arithmetic.

A calendar is part of the chart state (``core/model.py``); this module counts working days and
parses the dialog's input. The layout uses the count to give every working day the same width and
non-working days none (``core/timescale.py``).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import parse_qs

from librecharts.core.gantt import to_date
from librecharts.core.model import Calendar
from librecharts.core.value_line import check_date


def is_working(calendar: Calendar, day: date) -> bool:
    """Whether ``day`` is a working day of ``calendar``."""
    return day.weekday() in calendar.working_days and day not in calendar.holidays


def working_between(calendar: Calendar, start: date, end: date) -> int:
    """The number of working days in ``[start, end)``.

    Counted as whole weeks plus the remaining days, minus the holidays in the range. O(holidays),
    so a scale of decades stays cheap.
    """
    if end <= start:
        return 0
    weeks, rest = divmod((end - start).days, 7)
    count = weeks * len(calendar.working_days)
    first = start + timedelta(days=weeks * 7)
    count += sum(
        1
        for offset in range(rest)
        if (first + timedelta(days=offset)).weekday() in calendar.working_days
    )
    count -= sum(
        1
        for holiday in calendar.holidays
        if start <= holiday < end and holiday.weekday() in calendar.working_days
    )
    return count


def active(calendar: Calendar) -> bool:
    """Whether ``calendar`` hides any day: fewer than seven working weekdays or a holiday."""
    return len(calendar.working_days) < 7 or bool(calendar.holidays)


def check_holidays(text: str, language: str) -> tuple[date, ...] | str:
    """The holidays in ``text`` (one per line, or separated by commas or semicolons), or an error.

    Dates follow the date-line rules: ISO always, ``30.6.2026`` always, slashes month-first in
    English and day-first otherwise.
    """
    days: list[date] = []
    for part in re.split(r"[\n,;]+", text):
        part = part.strip()
        if not part:
            continue
        value = check_date(part, language)
        if isinstance(value, str):
            return "working_days_bad_date"
        day = to_date(value)
        if day is None:
            return "working_days_bad_date"
        days.append(day)
    return tuple(sorted(set(days)))


def changed(current: Calendar, query: str, language: str) -> Calendar:
    """``current`` with the working days or holidays in ``query`` replaced.

    ``working`` holds ISO weekday numbers (1 = Monday, 7 = Sunday), ``holidays`` dates as in
    :func:`check_holidays`. A missing field keeps the current value. Raises ``ValueError`` for an
    invalid query.
    """
    args = {
        key: values[-1]
        for key, values in parse_qs(query, strict_parsing=True, keep_blank_values=True).items()
    }
    unknown = set(args) - {"working", "holidays"}
    if unknown:
        raise ValueError(f"unknown working-days option: {sorted(unknown)[0]!r}")
    working = current.working_days
    if "working" in args:
        working = _weekdays(args["working"])
    holidays = current.holidays
    if "holidays" in args:
        parsed = check_holidays(args["holidays"], language)
        if isinstance(parsed, str):
            raise ValueError(parsed)
        holidays = parsed
    return Calendar(working, holidays)


def _weekdays(text: str) -> tuple[int, ...]:
    """ISO weekday numbers (1..7) as Python weekdays (0..6), sorted and unique."""
    days: list[int] = []
    for part in text.split(","):
        part = part.strip()
        try:
            day = int(part)
        except ValueError:
            raise ValueError(f"working days must be numbers, not {part!r}") from None
        if not 1 <= day <= 7:
            raise ValueError("working days are numbers from 1 (Monday) to 7 (Sunday)")
        days.append(day - 1)
    if not days:
        raise ValueError("a calendar needs at least one working day")
    return tuple(sorted(set(days)))
