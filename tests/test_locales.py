"""Translations (M21, ADR 0031): the JSON files of ``core/locales/`` and how they are used."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from build_oxt import build, localized_addons
from locales import content

from librecharts.core import messages
from librecharts.core.messages import (
    LOCALES,
    MESSAGES,
    SOURCE_LANGUAGES,
    addon_title,
    languages,
    text,
    translations,
)

ROOT = Path(__file__).parents[1]
SHIPPED = ("fr", "es", "it")  # complete translations that ship with the extension
PLACEHOLDER = re.compile(r"\{(\w+)\}")
LISTS = {"gantt_months": 12, "working_days_names": 7}  # comma-separated messages


def raw(code: str) -> dict[str, str]:
    return json.loads((LOCALES / f"{code}.json").read_text(encoding="utf-8"))


TRANSLATED = [code for code in languages() if code not in SOURCE_LANGUAGES]
PAIRS = [(code, key) for code in TRANSLATED for key in sorted(raw(code))]


@pytest.mark.parametrize("code", SOURCE_LANGUAGES)
def test_the_source_files_are_up_to_date(code: str) -> None:
    assert (LOCALES / f"{code}.json").read_text(encoding="utf-8") == content(code), (
        "run `uv run poe locales`"
    )


def test_every_shipped_language_is_found() -> None:
    assert set(SHIPPED) <= set(TRANSLATED)
    assert languages()[:2] == ("en", "de")


@pytest.mark.parametrize("code", SHIPPED)
def test_shipped_translations_are_complete(code: str) -> None:
    assert set(raw(code)) == set(MESSAGES)


@pytest.mark.parametrize("code", TRANSLATED)
def test_a_translation_holds_known_keys_and_text_only(code: str) -> None:
    entries = raw(code)
    assert set(entries) <= set(MESSAGES), sorted(set(entries) - set(MESSAGES))
    assert all(isinstance(value, str) and value.strip() for value in entries.values())


@pytest.mark.parametrize(("code", "key"), PAIRS)
def test_placeholders_match_english(code: str, key: str) -> None:
    english = MESSAGES[key]["en"]
    assert set(PLACEHOLDER.findall(raw(code)[key])) == set(PLACEHOLDER.findall(english))


@pytest.mark.parametrize(("code", "key"), PAIRS)
def test_endings_match_english(code: str, key: str) -> None:
    english, translated = MESSAGES[key]["en"], raw(code)[key]
    for ending in ("...", ":", "?"):
        assert english.endswith(ending) == translated.endswith(ending), (code, key, ending)
    if english.endswith(".") and not english.endswith("..."):
        assert translated.endswith("."), (code, key)
    assert english.startswith(" ") == translated.startswith(" ")


@pytest.mark.parametrize("code", TRANSLATED)
@pytest.mark.parametrize(("key", "count"), sorted(LISTS.items()))
def test_lists_keep_their_length(code: str, key: str, count: int) -> None:
    if key in raw(code):
        assert len(raw(code)[key].split(",")) == count


def test_text_reads_a_translation_and_falls_back_to_english() -> None:
    assert text("datasheet_title", "fr-FR") == "Données LibreCharts"
    assert text("datasheet_title", "es_ES") == "Datos de LibreCharts"
    assert text("datasheet_title", "it") == "Dati LibreCharts"
    assert text("datasheet_title", "pt-BR") == "LibreCharts data"
    assert (
        text("corrupt_chart", "fr", detail="x") == "Les données de ce graphique sont illisibles : x"
    )


def test_german_and_english_never_come_from_the_files() -> None:
    assert translations("en") == {}
    assert translations("de") == {}
    assert translations("../en") == {}


def test_a_broken_translation_counts_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "xx.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "yy.json").write_text("[1, 2]", encoding="utf-8")
    (tmp_path / "zz.json").write_text(
        json.dumps({"datasheet_title": "Z", "unknown": "?", "button_ok": 3, "button_cancel": ""}),
        encoding="utf-8",
    )
    monkeypatch.setattr(messages, "LOCALES", tmp_path)
    translations.cache_clear()
    try:
        assert translations("xx") == {}
        assert translations("yy") == {}
        assert translations("zz") == {"datasheet_title": "Z"}
        assert text("button_ok", "zz") == "OK"
        assert languages() == ("en", "de", "xx", "yy", "zz")
    finally:
        translations.cache_clear()


def test_add_on_titles_come_from_the_messages() -> None:
    assert addon_title("InsertColumnChart", "fr") == "Insérer un histogramme"
    assert addon_title("Arrange?op=grid&columns=3", "it") == "Disponi in griglia, 3 colonne"
    assert addon_title("Unknown", "en") is None


def test_the_build_adds_every_language_to_the_add_on_titles() -> None:
    source = (ROOT / "extension" / "Addons.xcu").read_text(encoding="utf-8")
    built = localized_addons(source)
    ET.fromstring(built.encode("utf-8"))  # noqa: S314 - our own file
    for code in SHIPPED:
        assert f'<value xml:lang="{code}">{addon_title("EditData", code)}</value>' in built
    assert localized_addons(source, ()) == source


def test_the_package_carries_the_translations(tmp_path: Path) -> None:
    with zipfile.ZipFile(build(out_dir=tmp_path)) as oxt:
        names = set(oxt.namelist())
        addons = oxt.read("Addons.xcu").decode("utf-8")
    for code in SHIPPED:
        assert f"librecharts/core/locales/{code}.json" in names
        assert f'xml:lang="{code}"' in addons
