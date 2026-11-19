"""The UI strings outside ``core/messages.py``: the add-on menu and toolbar titles.

They live in ``extension/Addons.xcu`` as static XML in English and German; the build adds the other
languages from ``core/locales/`` (ADR 0031). These tests keep the XML in step with
``core/messages.py``, so menu, toolbar, context menu and sidebar agree.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from librecharts.core.messages import ADDON_KEYS, MESSAGES, addon_title

ROOT = Path(__file__).parents[1]
ADDONS = ROOT / "extension" / "Addons.xcu"
OOR = "{http://openoffice.org/2001/registry}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def entries() -> list[tuple[str, dict[str, str]]]:
    """Every add-on entry's command (without the protocol prefix) and its title by language."""
    root = ET.parse(ADDONS).getroot()  # noqa: S314 - our own file, not untrusted input
    result: list[tuple[str, dict[str, str]]] = []
    for node in root.iter("node"):
        url, title = None, {}
        for prop in node.findall("prop"):
            name = prop.get(OOR + "name")
            if name == "URL":
                value = prop.find("value")
                url = value.text if value is not None else None
            elif name == "Title":
                for value in prop.findall("value"):
                    language = value.get(XML_LANG)
                    if language:
                        title[language] = value.text
        if url and title:
            result.append((url.removeprefix("org.librecharts:"), title))
    return result


ENTRIES = entries()
TITLES = dict(ENTRIES)


def test_the_menu_and_the_toolbar_agree_on_a_command() -> None:
    seen: dict[str, dict[str, str]] = {}
    for command, title in ENTRIES:
        assert seen.setdefault(command, title) == title, command


@pytest.mark.parametrize("command", sorted(TITLES))
def test_every_add_on_title_exists_in_english_and_german(command: str) -> None:
    title = TITLES[command]
    assert set(title) == {"en-US", "de"}
    assert all(title.values())


@pytest.mark.parametrize("command", sorted(TITLES))
def test_add_on_titles_match_the_messages(command: str) -> None:
    title = TITLES[command]
    assert title["en-US"] == addon_title(command, "en")
    assert title["de"] == addon_title(command, "de")


def test_every_add_on_key_names_an_entry() -> None:
    assert set(ADDON_KEYS) <= set(TITLES)
    assert set(MESSAGES) >= set(ADDON_KEYS.values())
