import re

import pytest

from librecharts.core.messages import MESSAGES, text

PLACEHOLDER = re.compile(r"\{(\w+)\}")


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_every_message_exists_in_english_and_german(key: str) -> None:
    assert set(MESSAGES[key]) >= {"en", "de"}
    assert all(MESSAGES[key].values())


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_placeholders_match_between_languages(key: str) -> None:
    assert set(PLACEHOLDER.findall(MESSAGES[key]["en"])) == set(
        PLACEHOLDER.findall(MESSAGES[key]["de"])
    )


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_punctuation_and_spacing_match_between_languages(key: str) -> None:
    en, de = MESSAGES[key]["en"], MESSAGES[key]["de"]
    for ending in (".", ":", "..."):
        assert en.endswith(ending) == de.endswith(ending), (key, ending)
    assert en.startswith(" ") == de.startswith(" "), key
    assert en.endswith(" ") == de.endswith(" "), key


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("de-DE", "LibreCharts-Daten"), ("de", "LibreCharts-Daten"), ("en-US", "LibreCharts data")],
)
def test_locale_selects_language(locale: str, expected: str) -> None:
    assert text("datasheet_title", locale) == expected


@pytest.mark.parametrize("locale", ["fr-FR", "", "zz"])
def test_unsupported_locale_falls_back_to_english(locale: str) -> None:
    assert text("datasheet_title", locale) == "LibreCharts data"


def test_fields_are_filled_in() -> None:
    assert text("corrupt_chart", "en", detail="bad JSON").endswith(": bad JSON")
