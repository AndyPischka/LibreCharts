from dataclasses import replace

from librecharts.core.datasheet import sample_mekko_state, sample_state
from librecharts.core.menu import PROTOCOL, SEPARATOR, MenuItem, chart_menu
from librecharts.core.model import Annotation

EDIT = MenuItem("Edit chart data", PROTOCOL + "EditData")
ADD = (
    SEPARATOR,
    MenuItem("Add difference arrow", PROTOCOL + "PickAnnotation?kind=difference"),
    MenuItem("Add level difference", PROTOCOL + "PickAnnotation?kind=difference&style=level"),
    MenuItem("Add CAGR arrow", PROTOCOL + "PickAnnotation?kind=cagr"),
    MenuItem("Add axis break", PROTOCOL + "PickAnnotation?kind=axis_break"),
)


def commands(item: MenuItem) -> list[str]:
    return [child.command for child in item.children]


def test_column_chart_without_annotations_offers_data_and_arrows() -> None:
    assert chart_menu(sample_state(), "en-US") == MenuItem("LibreCharts", children=(EDIT, *ADD))


def test_other_charts_offer_the_data_only() -> None:
    assert chart_menu(sample_mekko_state(), "en-US").children == (EDIT,)


def test_annotations_are_listed_with_their_actions_and_remove_all() -> None:
    state = replace(
        sample_state(),
        annotations=(
            Annotation("difference", 0, 2),
            Annotation("cagr", 0, 1, series=1),
            Annotation("difference", 2, 1, style="level", label="absolute"),
            Annotation("axis_break", 1, 1),
        ),
    )
    items = chart_menu(state, "en-US").children[len(ADD) + 1 :]
    assert [item.title for item in items] == [
        "",
        "Difference 2023 → 2025",
        "CAGR 2023 → 2024 (Product B)",
        "Level difference 2025 → 2024",
        "Axis break 2024",
        "Remove all annotations",
    ]
    difference, cagr, level = items[1:4]
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
    assert commands(items[4]) == [PROTOCOL + "RemoveAnnotation?index=3"]
    assert items[-1].command == PROTOCOL + "RemoveAnnotations"


def test_hidden_annotations_are_not_listed_but_keep_their_index() -> None:
    state = replace(
        sample_state(),
        annotations=(Annotation("difference", 0, 9), Annotation("difference", 0, 1)),
    )
    listed = [item for item in chart_menu(state, "en-US").children if item.children]
    assert len(listed) == 1
    assert commands(listed[0])[-1] == PROTOCOL + "RemoveAnnotation?index=1"


def test_menu_is_translated() -> None:
    state = replace(sample_state(), annotations=(Annotation("difference", 0, 1),))
    titles = [item.title for item in chart_menu(state, "de-DE").children]
    assert "Diagrammdaten bearbeiten" in titles
    assert "Differenz 2023 → 2024" in titles
