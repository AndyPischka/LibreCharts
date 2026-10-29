from dataclasses import replace

from librecharts.core.datasheet import (
    sample_mekko_state,
    sample_state,
    sample_waterfall_state,
    state_from_table,
)
from librecharts.core.menu import PROTOCOL
from librecharts.core.model import Annotation, Link
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
            "InsertGanttChart",
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


def test_a_chart_with_its_own_data_offers_a_link() -> None:
    panel = content(sample_state(), True, "en-US")
    assert panel.link_status == ""
    assert [(b.title, b.command, b.enabled) for b in panel.link] == [
        ("Link data...", PROTOCOL + "LinkData", True)
    ]
    assert not content(None, False, "en-US").link[0].enabled


def test_a_linked_chart_shows_its_source_and_the_link_commands() -> None:
    link = Link("file:///C:/Reports/Sales.xlsx", "Sheet1", "A1:D4", updated="2026-10-29T14:03")
    panel = content(replace(sample_state(), link=link), True, "de-DE")
    assert panel.edit[0].title == "Diagrammdaten anzeigen"
    assert panel.link_status == (
        "Verknüpft mit Sales.xlsx, Sheet1!A1:D4, aktualisiert 29.10.2026 14:03."
    )
    assert [b.command for b in panel.link] == [
        PROTOCOL + c for c in ("UpdateLink", "LinkData", "OpenSource", "RemoveLink")
    ]
    assert all(b.enabled for b in panel.link)


def test_update_all_links_is_always_offered() -> None:
    for panel in (content(None, False, "en-US"), content(sample_state(), True, "en-US")):
        assert panel.update_all.command == PROTOCOL + "UpdateAllLinks"
        assert panel.update_all.enabled


def test_element_and_arrange_buttons_follow_the_selection() -> None:
    none = content(None, False, "en-US")
    assert [b.enabled for b in none.elements] == [True, True, False]
    assert not any(b.enabled for b in none.arrange)

    two = content(None, False, "en-US", element_selected=True, shapes_selected=2)
    assert two.elements[2].enabled
    assert all(b.enabled for b in two.arrange)

    three = content(None, False, "en-US", shapes_selected=3)
    swap = [b for b in three.arrange if b.command.endswith("op=swap")]
    assert [b.enabled for b in swap] == [False]
    assert sum(b.enabled for b in three.arrange) == len(three.arrange) - 1


def test_agenda_buttons_follow_the_agenda_and_the_current_slide() -> None:
    commands = [PROTOCOL + c for c in ("InsertAgenda", "StartChapter", "UpdateAgenda")]
    none = content(None, False, "en-US")
    assert [b.command for b in none.agenda] == commands
    assert [b.enabled for b in none.agenda] == [True, False, False]

    content_slide = content(None, False, "de-DE", has_agenda=True)
    assert [b.title for b in content_slide.agenda] == [
        "Agenda einfügen",
        "Kapitel hier beginnen",
        "Agenda aktualisieren",
    ]
    assert [b.enabled for b in content_slide.agenda] == [True, True, True]

    agenda_slide = content(None, False, "en-US", has_agenda=True, agenda_slide=True)
    assert [b.enabled for b in agenda_slide.agenda] == [True, False, True]
