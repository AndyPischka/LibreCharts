from dataclasses import replace

import pytest

from librecharts.core import links
from librecharts.core.datasheet import sample_gantt_state, sample_state
from librecharts.core.links import Problem
from librecharts.core.model import Link

LINK = Link("file:///C:/Reports/data/Sales%202026.xlsx", "Sheet1", "B2:F6")


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("B2:F6", ("", "B2:F6")),
        ("  b2:f6 ", ("", "B2:F6")),
        ("$B$2:$F$6", ("", "B2:F6")),
        ("F6:B2", ("", "B2:F6")),
        ("B6:F2", ("", "B2:F6")),
        ("Sheet1!B2:F6", ("Sheet1", "B2:F6")),
        ("$Sheet1.$B$2:$F$6", ("Sheet1", "B2:F6")),
        ("'My sheet'!A1:C3", ("My sheet", "A1:C3")),
        ("'It''s'.A1:C3", ("It's", "A1:C3")),
        ("AA10:XFD1048576", ("", "AA10:XFD1048576")),
    ],
)
def test_ranges_are_read_as_typed_or_pasted(typed: str, expected: tuple[str, str]) -> None:
    assert links.parse_reference(typed) == expected


@pytest.mark.parametrize(
    "typed",
    [
        "",
        "B2",
        "B2:F",
        "Sales",
        "A0:B2",
        "A1:XFE2",
        "A1:B1048577",
        "Sheet1B2:F6",
        "!B2:F6",
        "B2:F6x",
    ],
)
def test_anything_else_is_no_range(typed: str) -> None:
    assert links.parse_reference(typed) is None


def test_addresses_are_built_from_indices() -> None:
    assert links.address(1, 1, 5, 5) == "B2:F6"
    assert links.address(0, 0, 25, 0) == "A1:Z1"
    assert links.address(26, 9, 701, 9) == "AA10:ZZ10"
    assert links.address(702, 0, 16_383, 0) == "AAA1:XFD1"


@pytest.mark.parametrize(
    ("sheet", "typed", "expected"),
    [
        ("Sheet1", "B2:F6", ("Sheet1", "B2:F6")),
        ("Sheet1", "Data!B2:F6", ("Data", "B2:F6")),
        ("", "Data!B2:F6", ("Data", "B2:F6")),
        ("Sheet1", "Revenue", ("", "Revenue")),
        ("", "_monthly.sales", ("", "_monthly.sales")),
        ("", "Umsätze", ("", "Umsätze")),
        ("", "B2:F6", "link_no_sheet_given"),
        ("Sheet1", "  ", "link_no_range_given"),
        ("Sheet1", "2024 sales", "link_bad_range"),
        ("Sheet1", "A:D", "link_bad_range"),
    ],
)
def test_the_dialog_fields_give_a_target_or_what_is_wrong(
    sheet: str, typed: str, expected: tuple[str, str] | str
) -> None:
    assert links.target(sheet, typed) == expected


@pytest.mark.parametrize(
    ("rows", "columns", "expected"),
    [
        (2, 2, None),
        (1, 5, "link_too_small"),
        (5, 1, "link_too_small"),
        (100, 100, None),
        (101, 100, "link_too_large"),
    ],
)
def test_a_range_needs_names_and_values_but_not_too_many(
    rows: int, columns: int, expected: str | None
) -> None:
    assert links.check_size(rows, columns) == expected


@pytest.mark.parametrize(
    ("source", "base", "expected"),
    [
        ("file:///C:/Reports/sales.xlsx", "file:///C:/Reports/deck.odp", "sales.xlsx"),
        ("file:///C:/Reports/data/sales.xlsx", "file:///C:/Reports/deck.odp", "data/sales.xlsx"),
        ("file:///C:/Data/sales.xlsx", "file:///C:/Reports/2026/deck.odp", "../../Data/sales.xlsx"),
        ("file:///c:/Data/sales.xlsx", "file:///C:/Reports/deck.odp", "../Data/sales.xlsx"),
        ("file:///D:/Data/sales.xlsx", "file:///C:/Reports/deck.odp", ""),
        ("file:///home/ana/sales.ods", "file:///home/ana/decks/deck.odp", "../sales.ods"),
        ("file://server/share/a/x.ods", "file://server/share/b/deck.odp", "../a/x.ods"),
        ("file://server/other/x.ods", "file://server/share/deck.odp", ""),
        ("file://server/x.ods", "file://server/share/deck.odp", ""),
        ("file:///C:/Reports/sales.xlsx", "", ""),
        ("https://example.org/sales.xlsx", "file:///C:/Reports/deck.odp", ""),
    ],
)
def test_sources_are_stored_relative_to_the_presentation_on_the_same_root(
    source: str, base: str, expected: str
) -> None:
    assert links.relative_url(source, base) == expected
    if expected:
        assert links.same_file(links.resolve(expected, base), source)


@pytest.mark.parametrize(
    ("relative", "base", "expected"),
    [
        ("sales.xlsx", "file:///E:/Moved/deck.odp", "file:///E:/Moved/sales.xlsx"),
        ("./data/../sales.xlsx", "file:///E:/Moved/deck.odp", "file:///E:/Moved/sales.xlsx"),
        ("../x.ods", "file:///tmp/a/deck.odp", "file:///tmp/x.ods"),
        ("../../x.ods", "file:///C:/deck.odp", ""),
        ("../x.ods", "file://server/share/deck.odp", ""),
        ("x.ods", "", ""),
        ("", "file:///C:/deck.odp", ""),
    ],
)
def test_relative_sources_resolve_next_to_the_presentation(
    relative: str, base: str, expected: str
) -> None:
    assert links.resolve(relative, base) == expected


def test_a_moved_folder_is_searched_first_then_the_old_place() -> None:
    link = replace(LINK, relative="data/Sales%202026.xlsx")
    assert links.candidates(link, "file:///E:/Moved/deck.odp") == (
        "file:///E:/Moved/data/Sales%202026.xlsx",
        LINK.url,
    )
    assert links.candidates(link, "file:///C:/Reports/deck.odp") == (LINK.url,)
    assert links.candidates(LINK, "file:///E:/Moved/deck.odp") == (LINK.url,)


def test_windows_paths_ignore_case_and_encoding_but_unix_paths_do_not() -> None:
    assert links.same_file("file:///C:/Data/Umsatz.ods", "file:///c:/data/umsatz.ods")
    assert links.same_file("file:///C:/My%20Data/x.ods", "file:///C:/My Data/x.ods")
    assert links.same_file("file://Server/Share/x.ods", "file://server/share/X.ODS")
    assert not links.same_file("file:///home/Ana/x.ods", "file:///home/ana/x.ods")
    assert links.same_file("https://example.org/a%20b.ods", "https://example.org/a b.ods")


def test_the_source_is_described_by_file_name_and_range() -> None:
    assert links.file_name(LINK.url) == "Sales 2026.xlsx"
    assert links.describe(LINK) == "Sales 2026.xlsx, Sheet1!B2:F6"
    assert links.describe(replace(LINK, sheet="", range="Revenue")) == "Sales 2026.xlsx, Revenue"


def test_fetched_data_keeps_names_as_shown_and_values_as_numbers() -> None:
    results = (
        ("", 46023.0, 46054.0),
        ("Revenue", 12.0, 12.5),
        ("Costs", "n/a", ""),
        (101.0, None, 3.0),
    )
    shown = (
        ("", "Jan 2026", "Feb 2026"),
        ("Revenue", "12", "12,50 €"),
        ("Costs", "n/a", ""),
        ("101", "#DIV/0!", "3"),
    )
    state = links.fetched(sample_state(), LINK, results, shown)
    assert state.link == LINK
    assert state.cells == (
        ("", "Jan 2026", "Feb 2026"),
        ("Revenue", "12", "12.5"),
        ("Costs", "n/a", ""),
        ("101", "#DIV/0!", "3"),
    )
    assert state.values == (
        (None, 46023.0, 46054.0),
        (None, 12.0, 12.5),
        (None, None, None),
        (101.0, None, 3.0),
    )
    assert state.kind == "column"


def test_fetched_grids_must_have_the_same_shape() -> None:
    with pytest.raises(ValueError, match="zip"):
        links.fetched(sample_state(), LINK, (("a", 1.0),), (("a",),))


def test_gantt_dates_stay_serial_numbers() -> None:
    gantt = sample_gantt_state()
    results = (("Activity", "Start", "End"), ("Concept", 46027.0, 46080.0))
    shown = (("Activity", "Start", "End"), ("Concept", "05.01.26", "27.02.26"))
    state = links.fetched(gantt, LINK, results, shown)
    assert state.cells[1] == ("Concept", "46027", "46080")
    assert state.values[1][1:] == (46027.0, 46080.0)


def test_the_read_only_view_writes_numbers_and_text() -> None:
    results = (("", 2024.0, "2025"), ("Revenue", 12.0, ""), (5.0, 1.5, "x"))
    shown = (("", "2024", "2025"), ("Revenue", "12", ""), ("5", "1.5", "x"))
    state = links.fetched(sample_state(), LINK, results, shown)
    assert links.view(state) == (("", "2024", "2025"), ("Revenue", 12.0, ""), ("5", 1.5, "x"))


def test_an_update_with_the_same_cells_and_values_is_no_change() -> None:
    state = sample_state()
    assert links.same_data(state, replace(state, link=LINK))
    changed = replace(state, values=((None, 1.0, 2.0, 3.0), *state.values[1:]))
    assert not links.same_data(state, changed)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Label,X,Y", "44,34,76,1"),
        ("Label;X;Y;Text, with comma", "59,34,76,1"),
        ("Label\tX\tY", "9,34,76,1"),
        ("Label", "44,34,76,1"),
    ],
)
def test_csv_files_are_split_at_their_most_frequent_separator(line: str, expected: str) -> None:
    assert links.csv_options(line) == expected


def test_the_update_time_is_shown_per_language() -> None:
    assert links.updated_text("2026-10-29T14:03", "de") == "29.10.2026 14:03"
    assert links.updated_text("2026-10-29T14:03", "en") == "2026-10-29 14:03"
    assert links.updated_text("yesterday", "en") == "yesterday"


def test_the_status_names_the_source_and_the_last_update() -> None:
    assert links.status(LINK, "en-US") == "Linked to Sales 2026.xlsx, Sheet1!B2:F6."
    updated = replace(LINK, updated="2026-10-29T14:03")
    assert (
        links.status(updated, "de-DE")
        == "Verknüpft mit Sales 2026.xlsx, Sheet1!B2:F6, aktualisiert 29.10.2026 14:03."
    )


def test_problems_are_explained_with_file_sheet_and_range() -> None:
    assert links.reason("link_missing", LINK, "en") == "The file Sales 2026.xlsx was not found."
    assert links.reason("link_no_sheet", LINK, "de") == (
        "In Sales 2026.xlsx gibt es keine Tabelle 'Sheet1'."
    )
    assert "10000" in links.reason("link_too_large", LINK, "en")


def test_the_report_of_a_single_update_says_only_what_the_user_cannot_see() -> None:
    problem = Problem(2, LINK, "link_no_range")
    assert links.report(0, 0, [problem], "en", single=True) == (
        "There is no range 'B2:F6' in Sales 2026.xlsx."
    )
    assert links.report(1, 0, [], "en", single=True) == "The linked data has not changed."
    assert links.report(1, 1, [], "en", single=True) == ""


def test_the_report_of_all_updates_counts_and_lists_the_problems() -> None:
    assert links.report(0, 0, [], "en") == "This presentation has no linked charts."
    assert links.report(3, 2, [], "en") == "2 of 3 linked charts changed."
    problems = [Problem(2, LINK, "link_missing"), Problem(5, LINK, "link_too_small")]
    assert links.report(1, 1, problems, "de").splitlines() == [
        "1 von 1 verknüpften Diagrammen geändert.",
        "Nicht aktualisiert:",
        "Folie 2: Die Datei Sales 2026.xlsx wurde nicht gefunden.",
        "Folie 5: Der Bereich braucht mindestens zwei Zeilen und zwei Spalten.",
    ]
    assert links.report(0, 0, problems[:1], "en").splitlines()[0] == "Not updated:"


def test_a_link_needs_a_source_and_a_range() -> None:
    with pytest.raises(ValueError, match="URL"):
        Link(" ", "Sheet1", "B2:F6")
    with pytest.raises(ValueError, match="range"):
        Link(LINK.url, "Sheet1", "")
