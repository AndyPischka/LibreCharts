from dataclasses import replace

from librecharts.core import style
from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.menu import PROTOCOL, SEPARATOR, MenuItem, chart_menu
from librecharts.core.model import Annotation, Format

FORMAT_STATE = Format(axis=True, gridlines=True, series_names="labels")

EDIT = MenuItem("Edit chart data", PROTOCOL + "EditData")
VARIANTS = (
    MenuItem("Show clustered", PROTOCOL + "ChangeChart?grouping=clustered"),
    MenuItem("Show as 100 %", PROTOCOL + "ChangeChart?percent=true"),
)
LINES = MenuItem(
    "Series as lines",
    children=(
        MenuItem("Product A as line", PROTOCOL + "ChangeChart?line=0&on=true"),
        MenuItem("Product B as line", PROTOCOL + "ChangeChart?line=1&on=true"),
        MenuItem("Product C as line", PROTOCOL + "ChangeChart?line=2&on=true"),
    ),
)
SORT = MenuItem(
    "Sort categories",
    children=(
        MenuItem("Descending", PROTOCOL + "ChangeChart?sort=descending"),
        MenuItem("Ascending", PROTOCOL + "ChangeChart?sort=ascending"),
    ),
)
SERIES = MenuItem(
    "Series names",
    children=(
        MenuItem("Show series labels", PROTOCOL + "ChangeFormat?series_names=labels"),
        MenuItem("Show legend", PROTOCOL + "ChangeFormat?series_names=legend"),
    ),
)
NUMBER_FORMAT = MenuItem("Number format...", PROTOCOL + "NumberFormat")
FORMAT = MenuItem(
    "Format",
    children=(
        MenuItem("Show value axis", PROTOCOL + "ChangeFormat?axis=true"),
        SERIES,
        NUMBER_FORMAT,
    ),
)
FORMAT_MEKKO = MenuItem("Format", children=(SERIES, NUMBER_FORMAT))
FORMAT_WATERFALL = MenuItem(
    "Format",
    children=(MenuItem("Show value axis", PROTOCOL + "ChangeFormat?axis=true"), NUMBER_FORMAT),
)
ADD = (
    SEPARATOR,
    MenuItem("Add difference arrow", PROTOCOL + "PickAnnotation?kind=difference"),
    MenuItem("Add level difference", PROTOCOL + "PickAnnotation?kind=difference&style=level"),
    MenuItem("Add CAGR arrow", PROTOCOL + "PickAnnotation?kind=cagr"),
    MenuItem("Add axis break", PROTOCOL + "AxisBreak"),
    MenuItem("Add value line...", PROTOCOL + "ValueLine"),
)
FORMAT_TOOLS = (
    SEPARATOR,
    MenuItem("Copy chart format", PROTOCOL + "CopyChartFormat"),
    MenuItem("Apply chart format", PROTOCOL + "ApplyChartFormat"),
)


def colour_menu(*names: str) -> MenuItem:
    """The "Series colour" submenu with every palette entry per series."""
    return MenuItem(
        "Series colour",
        children=tuple(
            MenuItem(
                name,
                children=tuple(
                    MenuItem(
                        f"Colour {index}",
                        PROTOCOL + f"ChangeChart?color={series}&palette={index - 1}",
                    )
                    for index in range(1, len(style.PALETTE) + 1)
                ),
            )
            for series, name in enumerate(names)
        ),
    )


def commands(item: MenuItem) -> list[str]:
    return [child.command for child in item.children]


def test_column_chart_without_annotations_offers_data_variants_sort_format_and_arrows() -> None:
    assert chart_menu(sample_state(), "en-US") == MenuItem(
        "LibreCharts",
        children=(
            EDIT,
            *VARIANTS,
            LINES,
            colour_menu("Product A", "Product B", "Product C"),
            SORT,
            FORMAT,
            *FORMAT_TOOLS,
            *ADD,
        ),
    )


def test_bar_charts_offer_the_same_variants_and_annotations() -> None:
    assert chart_menu(replace(sample_state(), kind="bar"), "en-US").children == (
        EDIT,
        *VARIANTS,
        colour_menu("Product A", "Product B", "Product C"),
        SORT,
        FORMAT,
        *FORMAT_TOOLS,
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
    sort = next(
        item for item in chart_menu(state, "en-US").children if item.title == "Sort categories"
    )
    assert [item.title for item in sort.children] == ["Data sheet order", "Ascending"]
    assert commands(sort) == [
        PROTOCOL + "ChangeChart?sort=none",
        PROTOCOL + "ChangeChart?sort=ascending",
    ]


def test_waterfall_charts_have_no_variants_or_sort() -> None:
    assert chart_menu(sample_waterfall_state(), "en-US").children == (
        EDIT,
        FORMAT_WATERFALL,
        *FORMAT_TOOLS,
        *ADD,
    )


def test_waterfall_annotations_are_titled_with_the_step_names() -> None:
    state = replace(sample_waterfall_state(), annotations=(Annotation("difference", 0, 5),))
    titles = [child.title for child in chart_menu(state, "en-US").children]
    assert "Difference Start → End" in titles


def test_a_percent_mekko_offers_the_data_the_switch_to_units_and_the_format() -> None:
    units = MenuItem("Show with units", PROTOCOL + "ChangeChart?percent=false")
    assert chart_menu(sample_mekko_state(), "en-US").children == (
        EDIT,
        units,
        colour_menu("Product A", "Product B", "Product C"),
        FORMAT_MEKKO,
        *FORMAT_TOOLS,
    )


def test_a_units_mekko_offers_the_switch_back_to_percent_and_an_axis() -> None:
    state = replace(sample_mekko_state(), percent=False)
    percent = MenuItem("Als 100 % anzeigen", PROTOCOL + "ChangeChart?percent=true")
    edit = MenuItem("Diagrammdaten bearbeiten", EDIT.command)
    items = chart_menu(state, "de-DE").children
    format_menu = next(item for item in items if item.title == "Format")
    assert items[:2] == (edit, percent)
    assert format_menu.title == "Format"
    assert "Wertachse anzeigen" in [child.title for child in format_menu.children]


def test_the_format_menu_hides_what_the_chart_already_shows() -> None:
    state = replace(sample_state(), format=FORMAT_STATE)
    format_menu = next(
        item for item in chart_menu(state, "en-US").children if item.title == "Format"
    )
    assert [child.title for child in format_menu.children] == [
        "Hide value axis",
        "Hide gridlines",
        "Series names",
        "Number format...",
    ]
    assert commands(format_menu)[0] == PROTOCOL + "ChangeFormat?axis=false"
    assert commands(format_menu)[1] == PROTOCOL + "ChangeFormat?gridlines=false"


def test_series_labels_and_legend_are_mutually_exclusive() -> None:
    state = replace(sample_state(), format=FORMAT_STATE)
    series = next(
        child
        for item in chart_menu(state, "en-US").children
        if item.title == "Format"
        for child in item.children
        if child.title == "Series names"
    )
    assert [child.title for child in series.children] == ["Hide series names", "Show legend"]
    assert all(
        child.command != PROTOCOL + "ChangeFormat?series_names=labels" for child in series.children
    )


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
    annotation_items = [
        item
        for item in items
        if item.children
        and item.title not in ("Series as lines", "Series colour", "Sort categories", "Format")
    ]
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
        if item.children
        and item.title not in ("Series as lines", "Series colour", "Sort categories", "Format")
    ]
    assert len(listed) == 1
    assert commands(listed[0])[-1] == PROTOCOL + "RemoveAnnotation?index=1"


def test_menu_is_translated() -> None:
    state = replace(sample_state(), annotations=(Annotation("difference", 0, 1),))
    titles = [item.title for item in chart_menu(state, "de-DE").children]
    assert "Diagrammdaten bearbeiten" in titles
    assert "Differenz 2023 → 2024" in titles
    assert "Kategorien sortieren" in titles
    assert "Format" in titles


def test_the_line_submenu_toggles_each_series_and_its_axis() -> None:
    state = replace(sample_state(), lines=(1,), secondary=(1,))
    lines = next(
        item for item in chart_menu(state, "en-US").children if item.title == "Series as lines"
    )
    assert [item.title for item in lines.children] == [
        "Product A as line",
        "Product B as column",
        "Product B on primary axis",
        "Product C as line",
    ]
    assert [item.command for item in lines.children] == [
        PROTOCOL + "ChangeChart?line=0&on=true",
        PROTOCOL + "ChangeChart?line=1&on=false",
        PROTOCOL + "ChangeChart?secondary=1&on=false",
        PROTOCOL + "ChangeChart?line=2&on=true",
    ]


def test_a_line_on_the_primary_axis_offers_the_secondary_one() -> None:
    state = replace(sample_state(), lines=(0,))
    lines = next(
        item for item in chart_menu(state, "en-US").children if item.title == "Series as lines"
    )
    assert "Product A on secondary axis" in [item.title for item in lines.children]
    assert [item.command for item in lines.children][1] == PROTOCOL + (
        "ChangeChart?secondary=0&on=true"
    )


def test_bar_and_100_percent_charts_have_no_line_submenu() -> None:
    for state in (
        replace(sample_state(), kind="bar"),
        replace(sample_state(), percent=True),
    ):
        titles = [item.title for item in chart_menu(state, "de-DE").children]
        assert "Reihen als Linien" not in titles


def test_line_and_area_charts_offer_their_own_annotations() -> None:
    line = state_from_table("line", "stacked", [[None, "2024"], ["Sales", 10]])
    area = state_from_table("area", "stacked", [[None, "2024"], ["Sales", 10]])
    line_titles = [item.title for item in chart_menu(line, "en-US").children]
    area_titles = [item.title for item in chart_menu(area, "en-US").children]
    assert "Add difference arrow" in line_titles
    assert "Add difference arrow" not in area_titles
    assert "Add value line..." in area_titles
    line_format = next(
        item for item in chart_menu(line, "en-US").children if item.title == "Format"
    )
    assert "Hide point markers" in [item.title for item in line_format.children]
