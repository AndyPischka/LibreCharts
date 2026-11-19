import json

import pytest

from librecharts.core import style
from librecharts.core.designcheck import (
    MAX_LISTED,
    DesignError,
    Margins,
    Rules,
    ShapeInfo,
    box_text,
    check,
    describe,
    fit_inside,
    nearest,
    report,
    rules_from_json,
    rules_to_json,
    same_scheme,
)

CORPORATE = style.Scheme("Corporate", (0x003366, 0xFF9900), font_name="Calibri")
RULES = Rules(
    CORPORATE, colors=(0x00AA00,), fonts=("Calibri Light",), margins=Margins(1000, 1000, 1000, 1000)
)
SLIDE = (28000, 15750)


def shape(**fields: object) -> ShapeInfo:
    values: dict[str, object] = {
        "slide": 0,
        "path": (0,),
        "label": "Box",
        "box": (2000, 2000, 5000, 3000),
    }
    values.update(fields)
    return ShapeInfo(**values)  # type: ignore[arg-type]


def test_a_shape_in_corporate_colours_and_fonts_inside_the_margins_is_clean() -> None:
    result = check(
        [
            shape(
                fill=0x003366,
                line=0x000000,
                fonts=("Calibri", "calibri light"),
                text_colors=(0xFFFFFF,),
            )
        ],
        RULES,
        CORPORATE,
        SLIDE,
    )
    assert result.clean
    assert result.fixes == ()
    assert result.scheme is None


def test_foreign_colours_and_fonts_are_found_with_their_nearest_corporate_replacement() -> None:
    result = check(
        [shape(fill=0x003399, line=0xFF8800, fonts=("Arial",), text_colors=(0x00BB00,))],
        RULES,
        CORPORATE,
        SLIDE,
    )
    assert [(f.issue, f.actual, f.expected) for f in result.findings] == [
        ("fill", "#003399", "#003366"),
        ("line", "#FF8800", "#FF9900"),
        ("text_color", "#00BB00", "#00AA00"),
        ("font", "Arial", "Calibri"),
    ]
    (fix,) = result.fixes
    assert fix.colors == {0x003399: 0x003366, 0xFF8800: 0xFF9900, 0x00BB00: 0x00AA00}
    assert fix.fonts == {"Arial": "Calibri"}
    assert fix.box is None


def test_a_shape_outside_the_margins_is_moved_back_and_a_too_large_one_shrinks() -> None:
    moved = check([shape(box=(-500, 14000, 5000, 3000))], RULES, CORPORATE, SLIDE)
    assert moved.fixes[0].box == (1000, 11750, 5000, 3000)
    assert moved.findings[0].issue == "position"
    huge = check([shape(box=(0, 0, 52000, 13750))], RULES, CORPORATE, SLIDE)
    x, y, width, height = huge.fixes[0].box or (0, 0, 0, 0)
    assert (x, y) == (1000, 1000)
    assert width == 26000
    assert height == round(13750 * 26000 / 52000)


def test_without_margins_positions_are_not_checked() -> None:
    rules = Rules(CORPORATE)
    assert check([shape(box=(-5000, -5000, 1000, 1000))], rules, CORPORATE, SLIDE).clean


def test_a_chart_deviates_through_the_document_scheme_and_its_position_only() -> None:
    chart = shape(kind="chart", fill=0x123456, fonts=("Arial",), box=(500, 2000, 5000, 3000))
    result = check([chart], RULES, style.DEFAULT, SLIDE)
    assert [f.issue for f in result.findings] == ["scheme", "position"]
    assert result.findings[0].slide is None
    assert result.scheme == CORPORATE
    assert check([replace_box(chart)], RULES, CORPORATE, SLIDE).clean


def replace_box(info: ShapeInfo) -> ShapeInfo:
    return ShapeInfo(info.slide, info.path, info.label, info.kind, (2000, 2000, 5000, 3000))


def test_the_document_scheme_only_matters_when_there_is_a_chart() -> None:
    assert check([shape(fill=0x003366)], RULES, style.DEFAULT, SLIDE).clean


def test_a_scheme_with_another_name_but_the_same_look_matches() -> None:
    assert same_scheme(style.Scheme("Renamed", CORPORATE.palette, font_name="Calibri"), CORPORATE)
    assert not same_scheme(style.DEFAULT, CORPORATE)


def test_elements_and_children_of_groups_keep_their_box_out_of_the_check() -> None:
    element = shape(kind="element", fill=0x123456, box=None)
    child = shape(path=(0, 1), box=None, fill=0x003366)
    assert check([element, child], RULES, CORPORATE, SLIDE).clean


def test_fit_inside_leaves_a_box_alone_when_the_margins_leave_no_room() -> None:
    assert fit_inside((0, 0, 10, 10), Margins(20000, 0, 20000, 0), SLIDE) == (0, 0, 10, 10)


def test_nearest_prefers_the_perceptually_closest_colour() -> None:
    assert nearest(0xEEEEEE, (0x000000, 0xFFFFFF)) == 0xFFFFFF
    assert nearest(0x101010, (0x000000, 0xFFFFFF)) == 0x000000


def test_corporate_design_files_round_trip_with_their_check_rules() -> None:
    restored = rules_from_json(rules_to_json(RULES))
    assert restored == RULES
    assert rules_from_json(style.scheme_to_json(CORPORATE)) == Rules(CORPORATE)
    assert "check" not in json.loads(rules_to_json(Rules(CORPORATE)))


def test_a_corporate_file_with_margins_in_millimetres() -> None:
    raw = json.loads(style.scheme_to_json(CORPORATE))
    raw["check"] = {"margins_mm": {"left": 12.5, "top": 10}}
    assert rules_from_json(json.dumps(raw)).margins == Margins(1250, 1000, 0, 0)


@pytest.mark.parametrize(
    ("check_rules", "message"),
    [
        ([], "check must be a JSON object"),
        ({"sizes": []}, "unknown check rule"),
        ({"colors": "red"}, "list of colours"),
        ({"colors": [True]}, "invalid colour"),
        ({"colors": [0x1000000]}, "invalid colour"),
        ({"fonts": "Arial"}, "list of font names"),
        ({"fonts": [" "]}, "invalid font name"),
        ({"margins_mm": 5}, "must be a JSON object"),
        ({"margins_mm": {"middle": 1}}, "unknown margin"),
        ({"margins_mm": {"left": "1"}}, "must be a number"),
        ({"margins_mm": {"left": -1}}, "between 0 and"),
    ],
)
def test_malformed_check_rules_are_rejected(check_rules: object, message: str) -> None:
    raw = json.loads(style.scheme_to_json(CORPORATE))
    raw["check"] = check_rules
    with pytest.raises(DesignError, match=message):
        rules_from_json(json.dumps(raw))


def test_a_malformed_scheme_is_a_design_error() -> None:
    with pytest.raises(DesignError, match="invalid JSON"):
        rules_from_json("{")


def test_the_report_lists_findings_in_the_users_language() -> None:
    result = check([shape(fill=0x003399, label="Title")], RULES, style.DEFAULT, SLIDE)
    assert report(result, "en-US") == (
        "Deviations from the corporate design: 1\n"
        "- Slide 1, Title: fill colour #003399 instead of #003366"
    )
    assert report(result, "de-DE", fixed=True).startswith(
        "Abweichungen vom Corporate Design korrigiert: 1"
    )
    clean = check([], RULES, CORPORATE, SLIDE)
    assert report(clean, "en") == "The presentation follows the corporate design."


def test_the_report_counts_what_it_does_not_list() -> None:
    shapes = [shape(path=(index,), fill=0x123456) for index in range(MAX_LISTED + 3)]
    lines = report(check(shapes, RULES, CORPORATE, SLIDE), "en").split("\n")
    assert len(lines) == MAX_LISTED + 2
    assert lines[-1] == "... and 3 more."


def test_a_scheme_finding_has_no_slide() -> None:
    result = check([shape(kind="chart")], RULES, style.DEFAULT, SLIDE)
    assert describe(result.findings[0], "en") == (
        "charts use the colour scheme Default instead of Corporate"
    )


def test_box_text_is_in_centimetres() -> None:
    assert box_text((1000, 2500, 10000, 5000)) == "1.0/2.5 cm, 10.0 x 5.0 cm"
