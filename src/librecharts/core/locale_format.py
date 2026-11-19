"""How a language writes dates in numbers (M21, ADR 0031).

German writes ``30.06.2026``, French, Spanish and Italian ``30/06/2026``; every other language gets
the unambiguous ISO date ``2026-06-30``. The date fields of the dialogs accept all of them (see
``core/value_line.py``). Pure Python, no UNO.
"""

from __future__ import annotations

from datetime import date, datetime

DAY_FIRST: dict[str, str] = {"de": ".", "fr": "/", "es": "/", "it": "/"}  # language -> separator


def numeric_date(day: date, language: str, *, with_year: bool = True) -> str:
    """``day`` in the numeric style of ``language``; without the year ``30.06.`` or ``30/06``."""
    separator = DAY_FIRST.get(language)
    if separator is None:
        return day.isoformat() if with_year else f"{day.month:02d}-{day.day:02d}"
    short = f"{day.day:02d}{separator}{day.month:02d}"
    if not with_year:
        return short + "." if separator == "." else short
    return f"{short}{separator}{day.year}"


def numeric_datetime(moment: datetime, language: str) -> str:
    """A date and time such as ``30.06.2026 14:03`` or ``2026-06-30 14:03``."""
    return f"{numeric_date(moment.date(), language)} {moment:%H:%M}"
