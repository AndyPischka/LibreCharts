"""Chart format options: axes, gridlines, series names and number formats (ADR 0014).

Everything the user can switch through ``ChangeFormat`` and the number-format dialog is parsed and
validated here, so the adapter only moves values around. Pure Python, no UNO.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast
from urllib.parse import parse_qs

from librecharts.core.model import (
    ChartState,
    Format,
    Grouping,
    Magnitude,
    Separator,
    SeriesNames,
)
from librecharts.core.options import Switch

MAGNITUDE_SUFFIXES: dict[str, dict[int, str]] = {
    "en": {3: "k", 6: "M", 9: "bn"},
    "de": {3: "Tsd.", 6: "Mio.", 9: "Mrd."},
}
_COMMA_LANGUAGES = frozenset(
    {
        "bg",
        "cs",
        "da",
        "de",
        "el",
        "es",
        "fi",
        "fr",
        "hr",
        "hu",
        "it",
        "nb",
        "nl",
        "nn",
        "pl",
        "pt",
        "ro",
        "ru",
        "sk",
        "sl",
        "sr",
        "sv",
        "tr",
        "uk",
        "vi",
    }
)


def language_of(locale: str) -> str:
    """The two-letter language of a LibreOffice locale like ``de-DE``; ``en`` if unknown."""
    language = locale.split("-")[0].lower()
    return language if len(language) == 2 and language.isalpha() else "en"


def separator_for_locale(locale: str) -> str:
    """``","`` for locales that write decimal commas, else ``"."``."""
    return "," if language_of(locale) in _COMMA_LANGUAGES else "."


def magnitude_suffix(magnitude: int, language: str) -> str:
    """The localized suffix for a power of ten (``"Tsd."``, ``"Mio."``, ``"Mrd."``)."""
    suffixes = MAGNITUDE_SUFFIXES.get(language, MAGNITUDE_SUFFIXES["en"])
    return suffixes.get(magnitude, "")


def default_format(kind: str, grouping: Grouping, locale: str) -> Format:
    """The format a newly inserted chart starts with.

    A Mekko and a stacked column or bar chart name their series next to the last column (think-cell
    style); a clustered one uses a legend. New charts have no axis, like before M6.
    """
    if kind == "mekko":
        names: SeriesNames = "labels"
    elif kind in ("column", "bar"):
        names = "labels" if grouping == "stacked" else "legend"
    else:
        names = "none"
    return Format(
        series_names=names,
        separator=cast("Separator", separator_for_locale(locale)),
        language=language_of(locale),
    )


def supports(state: ChartState, option: str) -> bool:
    """Whether the chart kind (and variant) has the format option."""
    if option in ("axis", "gridlines"):
        return state.kind != "mekko" or not state.percent
    if option == "series_names":
        return state.kind in ("column", "bar", "mekko")
    return False


def changed(current: Format, query: str) -> Format:
    """``current`` with the format option in ``query`` (``axis=true``) applied.

    One key per call. Raises ``ValueError`` for missing, unknown or invalid arguments.
    """
    args = {key: values[-1] for key, values in parse_qs(query, strict_parsing=True).items()}
    if len(args) != 1:
        raise ValueError(f"expected exactly one format option, got {sorted(args)}")
    key, value = next(iter(args.items()))
    if key in ("axis", "gridlines"):
        flag = {"true": True, "false": False}.get(value)
        if flag is None:
            raise ValueError(f"{key} must be true or false, not {value!r}")
        return replace(current, **{key: flag})
    if key == "series_names":
        if value not in ("none", "labels", "legend"):
            raise ValueError(f"series_names must be none, labels or legend, not {value!r}")
        return replace(current, series_names=value)
    raise ValueError(f"unknown format option: {key!r}")


def settled(state: ChartState, current: Format, query: str) -> Format:
    """Apply ``query`` if the chart kind supports that option; else raise ``ValueError``."""
    key = query.partition("=")[0]
    if not supports(state, key):
        raise ValueError(f"a {state.kind} chart has no {key} option")
    return changed(current, query)


def format_options(state: ChartState) -> tuple[Switch, ...]:
    """The format switches the menu and the panel offer, the current values included."""
    switches: list[Switch] = []
    if supports(state, "axis"):
        switches.append(
            Switch(
                "menu_axis_hide" if state.format.axis else "menu_axis_show",
                f"ChangeFormat?axis={'false' if state.format.axis else 'true'}",
            )
        )
        if state.format.axis:  # gridlines are only drawn with an axis
            switches.append(
                Switch(
                    "menu_gridlines_hide" if state.format.gridlines else "menu_gridlines_show",
                    f"ChangeFormat?gridlines={'false' if state.format.gridlines else 'true'}",
                )
            )
    if supports(state, "series_names"):
        switches.extend(
            Switch(
                f"menu_series_{mode}",
                f"ChangeFormat?series_names={mode}",
                state.format.series_names == mode,
            )
            for mode in ("none", "labels", "legend")
        )
    return tuple(switches)


def number_format(
    current: Format,
    decimals: str,
    magnitude: str,
    unit: str,
    separator: str,
) -> Format | str:
    """Apply the number-format dialog's fields; the new format or the key of an error message.

    An empty ``decimals`` field means automatic. ``magnitude`` is ``"0"``, ``"3"``, ``"6"`` or
    ``"9"``; ``separator`` is ``"."`` or ``","``.
    """
    if decimals.strip().lower() in ("", "auto", "automatisch"):
        places = None
    else:
        try:
            places = int(decimals.strip())
        except ValueError:
            return "format_decimals_invalid"
        if not 0 <= places <= 4:
            return "format_decimals_invalid"
    if magnitude not in ("0", "3", "6", "9"):
        return "format_magnitude_invalid"
    if len(unit) > 10:
        return "format_unit_too_long"
    if separator not in (".", ","):
        return "format_separator_invalid"
    return replace(
        current,
        decimals=places,
        magnitude=cast("Magnitude", int(magnitude)),
        unit=unit,
        separator=separator,
    )
