from dataclasses import replace

from librecharts.core.datasheet import sample_mekko_state, sample_state, sample_waterfall_state
from librecharts.core.menu import PROTOCOL, SEPARATOR, MenuItem, chart_menu
from librecharts.core.model import Annotation

EDIT = MenuItem("Edit chart data", PROTOCOL + "EditData")
VARIANTS = (
    MenuItem("Show clustered", PROTOCOL + "ChangeChart?grouping=clustered"),
    MenuItem("Show as 100 %", PROTOCOL + "ChangeChart?percent=true"),
)
SORT = MenuItem(
    "Sort categories",
    children=(
        MenuItem("Descending", PROTOCOL + "ChangeChart?sort=descending"),
        MenuItem("Ascending", PROTOCOL + "ChangeChart?sort=ascending"),
    ),
)
ADD = (
    SEPARATOR,
    MenuItem("Add difference arrow", PROTOCOL + "PickAnnotation?kind=difference"),
    MenuItem("Add level difference", PROTOCOL + "PickAnnotation?kind=difference&style=level"),
    MenuItem("Add CAGR arrow", PROTOCOL + "PickAnnotation?kind=cagr"),
    MenuItem("Add axis break", PROTOCOL + "AxisBreak"),
)


def commands(item: MenuItem) -> list[str]:
    return [child.command for child in item.children]


def test_column_chart_without_annotations_offers_data_variants_sort_and_arrows() -> None:
    assert chart_menu(sample_state(), "en-US") == MenuItem(
        "LibreCharts", children=(EDIT, *VARIANTS, SORT, *ADD)
    )


def test_bar_charts_offer_the_same_variants_and_annotations() -> None:
    assert chart_menu(replace(sample_state(), kind="bar"), "en-US").children == (
        EDIT,
        *VARIANTS,
        SORT,
        *ADD,
    )


def test_clustered_charts_offer_the_other_variants() -> None:
    state = replace(sample_state(), grouping="clustered")
    titles = [item.title for item in chart_menu(state, "en-US").children]
    assert "Show clustered" not in titles
    assert "Show stacked" in titles
    assert "Show as 100 %" in titles


def test_a_100_percent_chart_offers_no_annotations() -> None:
    state = replace(sample_state(), percent=True)
    titles = [item.title for item in chart_menu(state, "en-US").children]
    assert "Add difference arrow" not in titles
    assert "Show stacked" in titles
    assert "Show clustered" in titles


def test_the_current_sort_order_is_not_offered_again() -> None:
    state = replace(sample_state(), sort="descending")
    sort = next(item for item in chart_menu(state, "en-US").children if item.children)
    assert [item.title for item in sort.children] == ["Data sheet order", "Ascending"]
    assert commands(sort) == [
        PROTOCOL + "ChangeChart?sort=none",
        PROTOCOL + "ChangeChart?sort=ascending",
    ]


def test_waterfall_charts_have_no_variants_or_sort() -> None:
    assert chart_menu(sample_waterfall_state(), "en-US").children == (EDIT, *ADD)


def test_waterfall_annotations_are_titled_with_the_step_names() -> None:
    state = replace(sample_waterfall_state(), annotations=(Annotation("difference", 0, 5),))
    titles = [child.title for child in chart_menu(state, "en-US").children]
    assert "Difference Start → End" in titles


def test_a_percent_mekko_offers_the_data_and_the_switch_to_units() -> None:
    units = MenuItem("Show with units", PROTOCOL + "ChangeChart?percent=false")
    assert chart_menu(sample_mekko_state(), "en-US").children == (EDIT, units)


def test_a_units_mekko_offers_the_switch_back_to_percent() -> None:
    state = replace(sample_mekko_state(), percent=False)
    percent = MenuItem("Als 100 % anzeigen", PROTOCOL + "ChangeChart?percent=true")
    edit = MenuItem("Diagrammdaten bearbeiten", EDIT.command)
    assert chart_menu(state, "de-DE").children == (edit, percent)


def test_annotations_are_listed_with_their_actions_and_remove_all() -> None:
    state = replace(
        sample_state(),
        annotations=(
            Annotation("difference", 0, 2),
            Annotation("cagr", 0, 1, series=1),
            Annotation("difference", 2, 1, style="level", label="absolute"),
            Annotation("axis_break", 0, 0, lower=10.0, upper=50.0),
        ),
    )
    items = chart_menu(state, "en-US").children
    annotation_items = [item for item in items if item.children and item.title != "Sort categories"]
    assert [item.title for item in annotation_items] == [
        "Difference 2023 → 2025",
        "CAGR 2023 → 2024 (Product B)",
        "Level difference 2025 → 2024",
        "Axis break (10-50)",
    ]
    difference, cagr, level, axis_break = annotation_items
    assert commands(difference) == [
        PROTOCOL + "ChangeAnnotation?index=0&label=absolute",
        PROTOCOL + "ChangeAnnotation?index=0&style=level",
        PROTOCOL + "RemoveAnnotation?index=0",
    ]
    assert commands(cagr) == [PROTOCOL + "RemoveAnnotation?index=1"]
    assert commands(level) == [
        PROTOCOL + "ChangeAnnotation?index=2&label=percent",
        PROTOCOL + "ChangeAnnotation?index=2&style=bracket",
        PROTOCOL + "RemoveAnnotation?index=2",
    ]
    assert commands(axis_break) == [
        PROTOCOL + "EditAxisBreak",
        PROTOCOL + "RemoveAnnotation?index=3",
    ]
    assert items[-1].command == PROTOCOL + "RemoveAnnotations"


def test_hidden_annotations_are_not_listed_but_keep_their_index() -> None:
    state = replace(
        sample_state(),
        annotations=(Annotation("difference", 0, 9), Annotation("difference", 0, 1)),
    )
    listed = [
        item
        for item in chart_menu(state, "en-US").children
        if item.children and item.title != "Sort categories"
    ]
    assert len(listed) == 1
    assert commands(listed[0])[-1] == PROTOCOL + "RemoveAnnotation?index=1"


def test_menu_is_translated() -> None:
    state = replace(sample_state(), annotations=(Annotation("difference", 0, 1),))
    titles = [item.title for item in chart_menu(state, "de-DE").children]
    assert "Diagrammdaten bearbeiten" in titles
    assert "Differenz 2023 → 2024" in titles
    assert "Kategorien sortieren" in titles
