"""The date scale of a Gantt chart: two levels of calendar units, e.g. weeks under months (M10).

The unit pair is chosen from the date range alone, never from the chart size (ADR 0007): the
finest pair whose lower level has at most ``MAX_UNITS`` units. The scale starts and ends on
boundaries of the lower unit. Dates are inclusive days; the scale's ``end`` is exclusive.

Labels are short and language-dependent ("Jan", "Q3", week numbers as plain numbers); the names
come from ``core/messages.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from librecharts.core.messages import text

Unit = Literal["day", "week", "month", "quarter", "year", "decade"]

# (lower, upper) unit pairs from fine to coarse; the last one is used for every longer range.
PAIRS: tuple[tuple[Unit, Unit], ...] = (
    ("day", "month"),
    ("week", "month"),
    ("month", "year"),
    ("quarter", "year"),
    ("year", "decade"),
)
MAX_UNITS = 40  # at most this many units on the lower level (if a coarser pair exists)
_MONTHS: dict[Unit, int] = {"month": 1, "quarter": 3, "year": 12, "decade": 120}


@dataclass(frozen=True, slots=True)
class Period:
    """One unit of the scale, from ``start`` to ``end`` (exclusive)."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class TimeScale:
    lower: Unit
    upper: Unit
    start: date
    end: date  # exclusive

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    def fraction(self, day: date) -> float:
        """Where the start of ``day`` lies on the scale: 0 at ``start``, 1 at ``end``."""
        return (day - self.start).days / self.days

    def periods(self, unit: Unit) -> tuple[Period, ...]:
        """The units of the scale, the first and last clipped to its range."""
        out: list[Period] = []
        current = floor(self.start, unit)
        while current < self.end:
            following = after(current, unit)
            out.append(Period(max(current, self.start), min(following, self.end)))
            current = following
        return tuple(out)

    def labelled(self, period: Period, unit: Unit) -> bool:
        """Whether ``period`` keeps at least half of its unit; a shorter cut-off end of the
        upper level stays unlabelled, its label would not fit."""
        start = floor(period.start, unit)
        return 2 * (period.end - period.start).days >= (after(start, unit) - start).days

    @property
    def years(self) -> int:
        """How many calendar years the scale touches."""
        return (self.end - timedelta(days=1)).year - self.start.year + 1


def time_scale(first: date, last: date) -> TimeScale:
    """The scale for the days ``first`` to ``last`` (both included)."""
    for lower, upper in PAIRS:
        start = floor(first, lower)
        end = after(floor(last, lower), lower)
        if (lower, upper) == PAIRS[-1] or _count(start, end, lower) <= MAX_UNITS:
            return TimeScale(lower, upper, start, end)
    raise AssertionError("unreachable: the last pair always matches")


def floor(day: date, unit: Unit) -> date:
    """The first day of the unit that contains ``day`` (weeks start on Monday)."""
    if unit == "day":
        return day
    if unit == "week":
        return day - timedelta(days=day.weekday())
    if unit == "month":
        return day.replace(day=1)
    if unit == "quarter":
        return date(day.year, (day.month - 1) // 3 * 3 + 1, 1)
    if unit == "year":
        return date(day.year, 1, 1)
    return date(day.year - day.year % 10, 1, 1)


def after(start: date, unit: Unit) -> date:
    """The first day of the unit following the one that starts at ``start``."""
    if unit == "day":
        return start + timedelta(days=1)
    if unit == "week":
        return start + timedelta(days=7)
    index = start.year * 12 + start.month - 1 + _MONTHS[unit]
    return date(index // 12, index % 12 + 1, 1)


def _count(start: date, end: date, unit: Unit) -> int:
    """The number of units from ``start`` to ``end``; stops counting above ``MAX_UNITS``."""
    count, current = 0, start
    while current < end and count <= MAX_UNITS:
        current = after(current, unit)
        count += 1
    return count


def label(day: date, unit: Unit, language: str, *, upper: bool = False) -> str:
    """The header text of the unit starting at ``day``; an upper month also names its year."""
    if unit == "day":
        return str(day.day)
    if unit == "week":  # the bare ISO week number: "KW 27" does not fit a narrow week
        return str(day.isocalendar()[1])
    if unit == "month":
        name = month_name(day.month, language)
        return f"{name} {day.year}" if upper else name
    if unit == "quarter":
        return text("gantt_quarter", language, number=str((day.month - 1) // 3 + 1))
    if unit == "year":
        return str(day.year)
    return text("gantt_decade", language, year=str(floor(day, "decade").year))


def month_name(month: int, language: str) -> str:
    """The abbreviated name of ``month`` (1-12)."""
    return text("gantt_months", language).split(",")[month - 1]


def format_date(day: date, language: str, *, with_year: bool = True) -> str:
    """A date label: ``30.06.2026`` in German, ``30 Jun 2026`` in English (``30.06.``, ``30 Jun``
    without the year)."""
    if language == "de":
        return f"{day.day:02d}.{day.month:02d}." + (str(day.year) if with_year else "")
    short = f"{day.day} {month_name(day.month, language)}"
    return f"{short} {day.year}" if with_year else short
