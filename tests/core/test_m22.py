"""M22: per-label overrides, focus, source and notes."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import focus, labels, notes
from librecharts.core.datasheet import parse, sample_state
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.column import layout_column
from librecharts.core.layout.common import decorations, legend_insets
from librecharts.core.model import ChartState, Focus, Format, LabelKey, LabelOffset, Note
from librecharts.core.primitives import Line, Marker, Rect, Text


def column() -> ChartState:
    return sample_state()


def test_a_focus_needs_at_least_one_index_and_unique_non_negative_indices() -> None:
    with pytest.raises(ValueError, match="at least one"):
        Focus()
    with pytest.raises(ValueError, match="unique"):
        Focus(series=(1, 1))
    with pytest.raises(ValueError, match="unique"):
        Focus(categories=(0, 0))
    with pytest.raises(ValueError, match="negative"):
        Focus(series=(-1,))


def test_focus_changes_add_remove_and_clear() -> None:
    state = column()
    added = focus.changed(state, "focus=series&index=1&on=true")
    assert added.focus == Focus(series=(1,))
    both = focus.changed(added, "focus=category&index=2&on=true")
    assert both.focus == Focus(series=(1,), categories=(2,))
    removed = focus.changed(both, "focus=series&index=1&on=false")
    assert removed.focus == Focus(categories=(2,))
    assert focus.changed(removed, "focus=none").focus is None
    assert focus.changed(removed, "clear=true").focus is None
    with pytest.raises(ValueError, match="negative"):
        focus.changed(state, "focus=series&index=-1&on=true")
    with pytest.raises(ValueError, match="on must"):
        focus.changed(state, "focus=series&index=1&on=maybe")
    with pytest.raises(ValueError, match="focus="):
        focus.changed(state, "focus=unknown&index=1")


def test_a_point_is_in_focus_when_its_series_or_its_category_is() -> None:
    f = Focus(series=(0,), categories=(1,))
    assert f.shown(0, 2)
    assert f.shown(2, 1)
    assert not f.shown(2, 2)


def test_apply_mutes_only_data_shapes_outside_the_focus() -> None:
    primitives = (
        Rect(0, 0, 10, 10, 0, category=0),
        Rect(10, 0, 10, 10, 1, category=1),
        Marker(5, 5, 1, category=1),
        Text(0, 0, 10, 10, "name", "left", "axis"),
        Text(0, 0, 10, 10, "label", "center", "value", key=LabelKey("value", 1, 1)),
    )
    muted = focus.apply(primitives, Focus(series=(0,)))
    assert muted[0].muted is False
    assert muted[1].muted is True
    assert muted[2].muted is True
    assert muted[3].muted is False  # axis text has no series or category
    assert muted[4].muted is True
    by_category = focus.apply(primitives, Focus(categories=(1,)))
    assert by_category[0].muted is True
    assert by_category[1].muted is False
    assert by_category[2].muted is False


def test_focus_survives_a_data_edit_with_a_dangling_index() -> None:
    state = replace(column(), focus=Focus(series=(7,)))
    assert focus.apply((Rect(0, 0, 1, 1, 0, category=0),), state.focus)[0].muted


def test_describe_names_the_focused_series_and_categories() -> None:
    state = replace(column(), focus=Focus(series=(0,), categories=(2, 9)))
    assert focus.describe(state, ("A", "B", "C"), ("x", "y", "z")) == "A, z"


def test_label_overrides_hide_and_retitle_without_moving_the_box() -> None:
    state = replace(
        column(),
        labels=(
            LabelOffset(LabelKey("value", 0, 0), 0.0, 0.0, hidden=True),
            LabelOffset(LabelKey("value", 0, 1), 0.0, 0.0, text="best"),
        ),
    )
    primitives = layout_chart(state, 2000, 10000)
    by_key = {p.key: p for p in primitives if isinstance(p, Text) and p.key is not None}
    assert by_key[LabelKey("value", 0, 0)].hidden
    assert by_key[LabelKey("value", 0, 1)].text == "best"
    assert not by_key[LabelKey("value", 0, 1)].hidden


def test_override_commands_keep_the_offset_and_can_be_reset() -> None:
    moved = replace(column(), labels=(LabelOffset(LabelKey("value", 0, 0), 100.0, 50.0),))
    hidden = labels.override(moved, "role=value&category=0&series=0&hidden=true")
    assert hidden.labels[0].dx == 100.0
    assert hidden.labels[0].hidden
    titled = labels.override(
        hidden, "role=value&category=0&series=0&text=best", command="SetLabelText"
    )
    assert titled.labels[0].text == "best"
    assert not titled.labels[0].hidden
    cleared = labels.override(
        titled, "role=value&category=0&series=0&text=", command="SetLabelText"
    )
    assert cleared.labels == moved.labels
    assert (
        labels.override(cleared, "role=value&category=0&series=0", command="ResetLabel").labels
        == ()
    )


def test_key_from_name_round_trips_and_rejects_other_names() -> None:
    key = LabelKey("total", 2)
    assert labels.key_from_name("librecharts-label:total:2:") == key
    assert labels.key_from_name("librecharts-label:value:1:3") == LabelKey("value", 1, 3)
    assert labels.key_from_name("Arrow 1") is None
    assert labels.key_from_name("librecharts-label:nope:1:") is None


def test_source_and_note_commands_edit_the_chart_content() -> None:
    state = column()
    sourced = notes.changed(state, "text=Own+survey", "SetSource")
    assert sourced.source == "Own survey"
    assert notes.changed(sourced, "text=", "SetSource").source == ""
    with_note = notes.changed(sourced, "text=Watch+this&x=0.25&y=0.5", "AddNote")
    assert with_note.notes == (Note("Watch this", 0.25, 0.5),)
    moved = notes.changed(with_note, "index=0&x=0.5&y=0.25", "MoveNote")
    assert moved.notes[0].x == 0.5
    assert notes.changed(moved, "index=0", "RemoveNote").notes == ()
    with pytest.raises(ValueError, match="index"):
        notes.changed(with_note, "index=3", "RemoveNote")


def test_a_note_must_have_text_and_a_position_in_the_box() -> None:
    with pytest.raises(ValueError, match="needs a text"):
        Note("", 0.5, 0.5)
    with pytest.raises(ValueError, match="between 0 and 1"):
        Note("x", 1.5, 0.5)
    with pytest.raises(ValueError, match="finite"):
        Note("x", 0.5, float("nan"))
    with pytest.raises(ValueError, match="200"):
        Note("x" * 201, 0.5, 0.5)


def test_source_notes_and_legend_positions_are_layout_output() -> None:
    state = replace(
        column(),
        source="Own survey",
        notes=(Note("Watch this", 0.25, 0.5),),
        format=Format(series_names="legend", legend="bottom"),
    )
    primitives = layout_column(parse(state), "stacked", 4000, 10000, fmt=state.format)
    extra = decorations(state, 4000, 10000, 900.0)
    source = next(p for p in extra if isinstance(p, Text) and p.role == "axis")
    assert source.text == "Own survey"
    assert source.y == 9100
    note = next(p for p in extra if isinstance(p, Text) and p.role == "note")
    assert (note.x, note.y) == (1000.0, 5000.0)
    assert note.name == "librecharts-note:0"
    assert legend_insets(state.format) == (0.0, 0.0, 0.0, 800.0)
    swatch = next(p for p in primitives if isinstance(p, Rect) and p.width == 250.0)
    assert swatch.y > 9000


def test_a_source_line_reserves_a_footer_band() -> None:
    from librecharts.core.layout.chart import layout_chart

    plain = layout_chart(column(), 4000, 10000)
    sourced = layout_chart(replace(column(), source="Own survey"), 4000, 10000)
    assert len(sourced) == len(plain) + 1
    source = next(p for p in sourced if isinstance(p, Text) and p.role == "axis")
    assert source.text == "Own survey"
    # the plot moved up by the footer band
    plain_base = next(p for p in plain if isinstance(p, Line))
    sourced_base = next(p for p in sourced if isinstance(p, Line))
    assert sourced_base.y1 == pytest.approx(plain_base.y1 - 900.0)
