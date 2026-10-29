from dataclasses import replace
from datetime import date

import pytest

from librecharts.core.datasheet import Cell, sample_gantt_state, state_from_table
from librecharts.core.gantt import parse_gantt, serial
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.gantt import DIAMOND, layout_gantt
from librecharts.core.model import Annotation, ChartState, Format
from librecharts.core.primitives import SHADE, Line, Polygon, Primitive, Rect, Text

HEADER = ["Activity", "Start", "End", "Remark", "Phase"]
WIDTH, HEIGHT = 20000.0, 12000.0


def day(month: int, number: int) -> int:
    return serial(date(2026, month, number))


def gantt(*rows: list[Cell]) -> ChartState:
    return state_from_table("gantt", "stacked", [HEADER, *rows])


def lay(state: ChartState, width: float = WIDTH, height: float = HEIGHT) -> tuple[Primitive, ...]:
    return layout_chart(state, width, height)


def texts(primitives: tuple[Primitive, ...]) -> dict[str, Text]:
    return {p.text: p for p in primitives if isinstance(p, Text)}


def bars(primitives: tuple[Primitive, ...]) -> list[Rect]:
    return [p for p in primitives if isinstance(p, Rect) and p.series >= 0]


def test_the_sample_draws_bars_phases_milestones_and_a_two_level_header() -> None:
    out = lay(sample_gantt_state())
    labels = texts(out)
    for expected in ("Concept", "Testing", "Go-live", "Jan 2026", "Jun 2026", "2", "27"):
        assert expected in labels, expected
    assert "Jul 2026" not in labels  # only the first days of July: too short for a label
    assert len([p for p in out if isinstance(p, Polygon)]) == 2  # milestones
    assert len(bars(out)) == 5 + 2  # activities and phase bars


def test_bars_run_from_the_start_of_the_first_to_the_end_of_the_last_day() -> None:
    out = lay(
        gantt(["A", day(1, 5), day(1, 11), None, None], ["B", day(1, 12), day(1, 18), "", ""])
    )
    first, second = bars(out)
    assert first.x + first.width == pytest.approx(second.x)
    assert first.width == pytest.approx(second.width)


def test_bars_take_the_colour_of_their_phase() -> None:
    out = lay(sample_gantt_state())
    assert [rect.series for rect in bars(out)] == [0, 0, 0, 1, 1, 1, 1]


def test_phases_and_headings_have_bold_labels() -> None:
    state = gantt(
        ["Phase", day(1, 5), day(1, 30), None, "x"],
        ["Bar", day(1, 5), day(1, 9), None, None],
        ["Heading", None, None, None, None],
    )
    labels = texts(lay(state))
    assert [labels[name].role for name in ("Phase", "Bar", "Heading")] == [
        "heading",
        "category",
        "heading",
    ]


def test_a_phase_is_a_thin_bar_with_ticks_at_both_ends() -> None:
    state = gantt(
        ["Phase", day(1, 5), day(1, 30), None, "x"], ["Bar", day(1, 5), day(1, 9), "", ""]
    )
    out = lay(state)
    phase, bar = bars(out)
    assert phase.height < bar.height
    ticks = [p for p in out if isinstance(p, Line) and p.role == "connector"]
    assert [tick.x1 for tick in ticks] == pytest.approx([phase.x, phase.x + phase.width])


def test_a_milestone_is_a_diamond_with_its_date() -> None:
    state = replace(
        gantt(["Go-live", day(6, 30), None, None, None], ["A", day(5, 1), day(6, 1), "", ""]),
        format=Format(language="de"),
    )
    out = lay(state)
    (diamond,) = [p for p in out if isinstance(p, Polygon)]
    xs = [x for x, _ in diamond.points]
    assert max(xs) - min(xs) == pytest.approx(DIAMOND)
    label = texts(out)["30.06."]  # one year on the scale: no year in the date
    assert label.x > max(xs) or label.x + label.width < min(xs)


def test_a_milestone_date_names_the_year_when_the_scale_spans_two() -> None:
    state = gantt(
        ["Start", serial(date(2025, 11, 3)), None, None, None],
        ["End", day(2, 2), None, None, None],
    )
    assert "3 Nov 2025" in texts(lay(state))


def test_the_milestone_remark_follows_its_date() -> None:
    state = gantt(["M", day(1, 5), None, "approved", None], ["A", day(1, 5), day(6, 1), "", ""])
    assert "5 Jan  approved" in texts(lay(state))


def test_remarks_go_right_left_or_inside_by_the_dates() -> None:
    state = gantt(
        ["Early", day(1, 5), day(1, 31), "right", None],
        ["Late", day(5, 1), day(6, 28), "left", None],
        ["Long", day(1, 5), day(6, 28), "inside", None],
    )
    out = lay(state)
    early, late, long = bars(out)
    labels = texts(out)
    assert labels["right"].x > early.x + early.width
    assert labels["right"].align == "left"
    assert labels["left"].x + labels["left"].width < late.x
    assert labels["left"].align == "right"
    assert labels["inside"].fill == long.series
    assert labels["inside"].x == pytest.approx(long.x)


def test_every_other_upper_unit_is_shaded() -> None:
    out = lay(sample_gantt_state())  # January to the first days of July
    shades = [p for p in out if isinstance(p, Rect) and p.series == SHADE]
    assert len(shades) == 3  # February, April, June


def test_gridlines_mark_the_lower_units_when_switched_on() -> None:
    state = sample_gantt_state()
    off = [p for p in lay(state) if isinstance(p, Line) and p.role == "grid"]
    on = [
        p
        for p in lay(replace(state, format=Format(gridlines=True)))
        if isinstance(p, Line) and p.role == "grid"
    ]
    assert len(on) - len(off) == 25  # 26 weeks, the first edge is the scale's start


def test_a_date_line_is_dashed_and_labelled_with_its_date() -> None:
    state = replace(
        sample_gantt_state(),
        annotations=(Annotation("value_line", 0, 0, value=float(day(3, 16))),),
    )
    out = lay(state)
    (line,) = [p for p in out if isinstance(p, Line) and p.role == "helper"]
    assert line.x1 == line.x2
    label = texts(out)["16 Mar"]
    assert label.role == "annotation"
    assert label.x < line.x1 < label.x + label.width


def test_a_date_line_outside_the_rows_extends_the_scale() -> None:
    state = replace(
        gantt(["A", day(3, 2), day(3, 20), None, None]),
        annotations=(Annotation("value_line", 0, 0, value=float(day(5, 25))),),
    )
    out = lay(state)
    (line,) = [p for p in out if isinstance(p, Line) and p.role == "helper"]
    (bar,) = bars(out)
    assert line.x1 > bar.x + bar.width
    assert "May 2026" in texts(out)


def test_sorting_by_start_reorders_the_rows() -> None:
    state = gantt(
        ["Late", day(3, 2), day(3, 20), None, None], ["Early", day(1, 5), day(1, 9), "", ""]
    )
    unsorted, ordered = lay(state), lay(replace(state, sort="ascending"))
    assert texts(unsorted)["Late"].y < texts(unsorted)["Early"].y
    assert texts(ordered)["Early"].y < texts(ordered)["Late"].y


def test_the_label_column_grows_with_the_longest_label_up_to_a_cap() -> None:
    short = bars(lay(gantt(["A", day(1, 5), day(1, 9), None, None])))[0]
    longer = bars(lay(gantt(["A rather long activity", day(1, 5), day(1, 9), None, None])))[0]
    huge = bars(lay(gantt(["x" * 300, day(1, 5), day(1, 9), None, None])))[0]
    assert short.x < longer.x < huge.x
    assert huge.x <= WIDTH * 0.35


def test_the_structure_does_not_depend_on_the_size() -> None:
    state = replace(
        sample_gantt_state(),
        format=Format(gridlines=True),
        annotations=(Annotation("value_line", 0, 0, value=float(day(3, 16))),),
    )

    def kinds(width: float, height: float) -> list[str]:
        return [type(p).__name__ for p in lay(state, width, height)]

    assert kinds(20000, 12000) == kinds(9000, 5000) == kinds(30000, 4000)


def test_rows_without_dates_draw_nothing() -> None:
    assert lay(gantt(["Heading", None, None, None, None])) == ()
    assert layout_gantt(parse_gantt(gantt()), WIDTH, HEIGHT) == ()


def test_too_small_a_box_is_rejected() -> None:
    with pytest.raises(ValueError, match="too small"):
        lay(sample_gantt_state(), 400, HEIGHT)
    with pytest.raises(ValueError, match="too small"):
        lay(sample_gantt_state(), WIDTH, 900)
