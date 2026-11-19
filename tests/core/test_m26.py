"""M26: distribute and align, process graphics and the icon set."""

from __future__ import annotations

import pytest

from librecharts.core import arrange, graphics, icons
from librecharts.core.arrange import Rect
from librecharts.core.menu import arrange_items
from librecharts.core.primitives import Text, bounds


def test_distribute_equal_gaps_keeps_the_outer_shapes() -> None:
    rects: list[Rect] = [(0, 0, 100, 100), (200, 0, 100, 100), (500, 0, 100, 100)]
    placed = arrange.distribute(rects, "h", "gaps")
    assert placed[0] == rects[0]
    assert placed[2] == rects[2]
    assert placed[1][0] - 0 - 100 == 500 - placed[1][0] - 100


def test_distribute_equal_centres_and_vertical_mode() -> None:
    rects: list[Rect] = [(0, 0, 100, 100), (0, 200, 100, 100), (0, 500, 100, 100)]
    placed = arrange.distribute(rects, "v", "centres")
    assert placed[1][1] == 250
    assert arrange.distribute(rects[:2], "v", "gaps") == rects[:2]


def test_align_uses_the_selection_bounding_box() -> None:
    rects: list[Rect] = [(0, 0, 100, 100), (300, 200, 50, 50)]
    assert arrange.align(rects, "left") == [(0, 0, 100, 100), (0, 200, 50, 50)]
    assert arrange.align(rects, "right")[1][0] == 300
    assert arrange.align(rects, "top")[1][1] == 0
    assert arrange.align(rects, "bottom")[0][1] == 150
    with pytest.raises(ValueError, match="edge"):
        arrange.align(rects, "middle")


def test_align_to_slide_with_and_without_margin() -> None:
    rects: list[Rect] = [(10, 20, 100, 50)]
    assert arrange.align_slide(rects, "left", 1000, 800) == [(0, 20, 100, 50)]
    assert arrange.align_slide(rects, "right", 1000, 800, 50) == [(850, 20, 100, 50)]
    assert arrange.align_slide(rects, "bottom", 1000, 800, 40) == [(10, 710, 100, 50)]
    assert arrange.align_slide(rects, "hcenter", 1000, 800) == [(450, 20, 100, 50)]


def test_a_graphic_name_round_trips() -> None:
    for item in (
        graphics.Graphic("process", 4, True),
        graphics.Graphic("chevron", 3, False),
        graphics.Graphic("pyramid", 2, False),
        graphics.Graphic("icon", icon="target"),
    ):
        assert graphics.parse(graphics.name(item)) == item
    assert graphics.parse("librecharts:chart") is None
    assert graphics.parse("librecharts-graphic:nope") is None


def test_graphic_validation() -> None:
    with pytest.raises(ValueError, match="steps"):
        graphics.Graphic("process", 0)
    with pytest.raises(ValueError, match="steps"):
        graphics.Graphic("process", 9)
    with pytest.raises(ValueError, match="vertical"):
        graphics.Graphic("pyramid", 3, True)
    with pytest.raises(ValueError, match="icon"):
        graphics.Graphic("icon", icon="nope")


def test_every_graphic_layout_stays_in_its_box() -> None:
    for item in (
        graphics.Graphic("process", 4, True),
        graphics.Graphic("chevron", 4, True),
        graphics.Graphic("pyramid", 4, False),
        graphics.Graphic("icon", icon="calendar"),
    ):
        for width, height in ((2000, 1000), (8000, 4000)):
            primitives = graphics.layout(item, width, height, ("A", "B", "C", "D"))
            for p in primitives:
                left, top, right, bottom = bounds(p)
                assert left >= 0
                assert top >= 0
                assert right <= width + 0.01
                assert bottom <= height + 0.01


def test_text_primitives_are_in_reading_order() -> None:
    primitives = graphics.layout(graphics.Graphic("process", 3), 6000, 2000)
    assert [p.text for p in primitives if isinstance(p, Text)] == ["Step 1", "Step 2", "Step 3"]


def test_every_icon_returns_primitives_inside_the_box() -> None:
    for name in icons.ICONS:
        for p in icons.primitives(name, 1000, 1000):
            left, top, right, bottom = bounds(p)
            assert left >= -0.01
            assert top >= -0.01
            assert right <= 1000.01
            assert bottom <= 1000.01
    with pytest.raises(ValueError, match="icon"):
        icons.primitives("nope", 1000, 1000)


def test_the_menu_offers_distribute_and_align() -> None:
    def leaves(items: tuple[object, ...]) -> list[str]:
        out: list[str] = []
        for item in items:
            if getattr(item, "command", ""):
                out.append(str(item.command))  # type: ignore[attr-defined]
            out.extend(leaves(getattr(item, "children", ())))
        return out

    commands = leaves(arrange_items("en"))
    assert any("op=distribute" in command for command in commands)
    assert any(command == "org.librecharts:Arrange?op=align&edge=left" for command in commands)
    assert any("op=align-slide" in command for command in commands)
