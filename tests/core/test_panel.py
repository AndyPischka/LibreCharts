from dataclasses import replace

from librecharts.core.datasheet import sample_mekko_state, sample_state, sample_waterfall_state
from librecharts.core.menu import PROTOCOL
from librecharts.core.model import Annotation
from librecharts.core.panel import content


def test_insert_buttons_are_always_enabled() -> None:
    panel = content(None, False, "en-US")
    assert [b.command for b in panel.insert] == [
        PROTOCOL + c
        for c in ("InsertColumnChart", "InsertBarChart", "InsertWaterfallChart", "InsertMekkoChart")
    ]
    assert all(b.enabled for b in panel.insert)


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


def test_other_charts_can_only_be_edited() -> None:
    panel = content(sample_mekko_state(), True, "en-US")
    assert panel.edit[0].enabled
    assert not any(b.enabled for b in panel.add)


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
