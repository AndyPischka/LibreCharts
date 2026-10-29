from dataclasses import replace

from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.menu import PROTOCOL
from librecharts.core.model import Annotation
from librecharts.core.panel import content


def test_insert_buttons_are_always_enabled() -> None:
    panel = content(None, False, "en-US")
    assert [b.command for b in panel.insert] == [
        PROTOCOL + c
        for c in (
            "InsertColumnChart",
            "InsertBarChart",
            "InsertLineChart",
            "InsertAreaChart",
            "InsertWaterfallChart",
            "InsertMekkoChart",
            "InsertPieChart",
            "InsertScatterChart",
            "InsertButterflyChart",
        )
    ]
    assert all(b.enabled for b in panel.insert)


def test_a_column_chart_offers_its_variants_and_the_sort_cycle() -> None:
    panel = content(sample_state(), True, "en-US")
    assert [b.command for b in panel.options] == [
        PROTOCOL + "ChangeChart?grouping=stacked",
        PROTOCOL + "ChangeChart?grouping=clustered",
        PROTOCOL + "ChangeChart?percent=true",
        PROTOCOL + "ChangeChart?sort=descending",
    ]
    # the current variant is shown but disabled
    assert [b.enabled for b in panel.options] == [False, True, True, True]


def test_a_100_percent_chart_says_so_and_disables_the_100_percent_button() -> None:
    panel = content(replace(sample_state(), percent=True), True, "en-US")
    assert panel.status.startswith("Column chart (100 %), ")
    assert [b.enabled for b in panel.options] == [True, True, False, True]


def test_without_a_chart_everything_else_is_disabled() -> None:
    panel = content(None, False, "en-US")
    assert panel.status == "No chart selected."
    assert not any(b.enabled for b in (*panel.edit, *panel.add, panel.remove_all))
    assert panel.rows == ()


def test_orphaned_chart_says_so_and_cannot_be_edited() -> None:
    panel = content(None, True, "en-US")
    assert "not in this presentation" in panel.status
    assert not any(b.enabled for b in (*panel.edit, *panel.add))


def test_column_chart_enables_edit_and_annotations() -> None:
    state = sample_state()
    panel = content(state, True, "en-US")
    assert panel.status.startswith("Column chart, ")
    assert all(b.enabled for b in (*panel.edit, *panel.add))
    assert not panel.remove_all.enabled
    assert panel.rows == ()


def test_bar_and_waterfall_charts_can_be_annotated() -> None:
    for state in (replace(sample_state(), kind="bar"), sample_waterfall_state()):
        panel = content(state, True, "en-US")
        assert all(b.enabled for b in (*panel.edit, *panel.add))


def test_a_mekko_can_only_be_edited_and_switched() -> None:
    panel = content(sample_mekko_state(), True, "en-US")
    assert panel.edit[0].enabled
    assert [b.title for b in panel.options] == ["Show with units"]
    assert panel.options[0].command == PROTOCOL + "ChangeChart?percent=false"
    assert all(b.enabled for b in panel.options)
    assert not any(b.enabled for b in panel.add)


def test_a_units_mekko_says_so_and_offers_percent() -> None:
    panel = content(replace(sample_mekko_state(), percent=False), True, "en-US")
    assert panel.status.startswith("Marimekko chart (units), ")
    assert panel.options[0].command == PROTOCOL + "ChangeChart?percent=true"


def test_only_charts_with_options_get_an_options_button() -> None:
    assert content(sample_waterfall_state(), True, "en-US").options == ()
    assert content(None, True, "en-US").options == ()
    assert content(None, False, "en-US").options == ()


def test_annotations_are_listed_with_their_remove_command() -> None:
    state = replace(
        sample_state(),
        annotations=(Annotation("difference", 0, 1), Annotation("axis_break", 0, 0)),
    )
    panel = content(state, True, "en-US")
    assert [r.remove for r in panel.rows] == [
        "RemoveAnnotation?index=0",
        "RemoveAnnotation?index=1",
    ]
    assert panel.rows[1].title == "Axis break (auto)"
    assert panel.remove_all.enabled


def test_annotations_that_are_not_drawn_are_not_listed() -> None:
    state = replace(sample_state(), annotations=(Annotation("difference", 0, 99),))
    assert content(state, True, "en-US").rows == ()


def test_texts_follow_the_locale() -> None:
    assert content(None, False, "de-DE").status == "Kein Diagramm ausgewählt."


def test_line_and_area_charts_report_their_kind() -> None:
    line = state_from_table("line", "stacked", [[None, "2024", "2025"], ["Sales", 1, 2]])
    area = state_from_table("area", "stacked", [[None, "2024", "2025"], ["Sales", 1, 2]])
    assert content(line, True, "en-US").status == "Line chart, 2 categories"
    assert content(area, True, "en-US").status == "Area chart, 2 categories"
    assert content(replace(area, percent=True), True, "en-US").status == (
        "Area chart (100 %), 2 categories"
    )


def test_a_combination_chart_reports_its_lines() -> None:
    panel = content(replace(sample_state(), lines=(1,)), True, "en-US")
    assert panel.status.startswith("Column chart with lines, ")


def test_line_and_area_charts_offer_only_their_annotation_buttons() -> None:
    area = state_from_table("area", "stacked", [[None, "2024"], ["Sales", 1]])
    enabled = {b.title: b.enabled for b in content(area, True, "en-US").add}
    assert "Add value line..." in enabled
    assert enabled["Add value line..."]
    assert not enabled["Add difference arrow"]
    assert not enabled["Add axis break"]
    line = state_from_table("line", "stacked", [[None, "2024"], ["Sales", 1]])
    assert all(b.enabled for b in content(line, True, "en-US").add)
