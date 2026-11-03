"""The UI strings outside ``core/messages.py``: the add-on menu and toolbar titles.

They live in ``extension/Addons.xcu`` as static XML, so they can drift from the context menu and
the sidebar. These tests keep the three copies in step.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from librecharts.core.messages import MESSAGES, text

ROOT = Path(__file__).parents[1]
ADDONS = ROOT / "extension" / "Addons.xcu"
OOR = "{http://openoffice.org/2001/registry}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Commands the add-on menu and toolbar share with the context menu and the sidebar. Their titles
# must be the same string, so a rename cannot leave one of the three behind.
SHARED = {
    "EditData": "menu_edit_data",
    "LinkData": "menu_link_data",
    "UpdateAllLinks": "menu_update_all_links",
    "SameScale": "menu_same_scale",
    "RemoveSameScale": "menu_remove_same_scale",
    "CopyChartFormat": "menu_copy_format",
    "ApplyChartFormat": "menu_apply_format",
    "MoveLabels": "menu_move_labels",
    "ResetLabels": "menu_reset_labels",
    "PickAnnotation?kind=difference": "menu_add_difference",
    "PickAnnotation?kind=difference&style=level": "menu_add_level",
    "PickAnnotation?kind=cagr": "menu_add_cagr",
    "AxisBreak": "menu_add_break",
    "Arrange?op=width": "menu_arrange_width",
    "Arrange?op=height": "menu_arrange_height",
    "Arrange?op=size": "menu_arrange_size",
    "Arrange?op=swap": "menu_arrange_swap",
    "InsertAgenda": "menu_insert_agenda",
    "StartChapter": "menu_start_chapter",
    "UpdateAgenda": "menu_update_agenda",
}
GRID = {f"Arrange?op=grid&columns={columns}": columns for columns in (2, 3, 4)}


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


@pytest.mark.parametrize(("command", "key"), sorted(SHARED.items()))
def test_add_on_titles_match_the_menu(command: str, key: str) -> None:
    title = TITLES[command]
    assert title["en-US"] == MESSAGES[key]["en"]
    assert title["de"] == MESSAGES[key]["de"]


@pytest.mark.parametrize(("command", "columns"), sorted(GRID.items()))
def test_grid_titles_match_the_menu(command: str, columns: int) -> None:
    title = TITLES[command]
    assert title["en-US"] == text("menu_arrange_grid", "en", columns=str(columns))
    assert title["de"] == text("menu_arrange_grid", "de", columns=str(columns))
