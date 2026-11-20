# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Process, chevron and pyramid graphics: insert, labels and undo (M26)."""

from helpers import dispatch, new_impress, uno_command

from librecharts.core import graphics
from librecharts.lo import graphics as lo_graphics


def _only(doc):
    found = lo_graphics.all_graphics(doc)
    assert len(found) == 1
    return found[0]


def _top_and_bottom_width(group):
    """Widths of the top and bottom edge of a pyramid's first step (read in one pass)."""
    for index in range(group.getCount()):
        child = group.getByIndex(index)
        if child.ShapeType != "com.sun.star.drawing.PolyPolygonShape":
            continue
        points = [(p.X, p.Y) for outer in child.PolyPolygon for p in outer]
        top, bottom = min(y for _, y in points), max(y for _, y in points)
        top_x = [x for x, y in points if y == top]
        bottom_x = [x for x, y in points if y == bottom]
        return max(top_x) - min(top_x), max(bottom_x) - min(bottom_x)
    raise AssertionError("the graphic has no polygon")


def test_the_sidebar_pyramid_command_inserts_a_vertical_pyramid(ctx):
    doc = new_impress(ctx)
    try:
        # The sidebar sends no direction; a pyramid has only a vertical form.
        dispatch(ctx, doc, "org.librecharts:InsertGraphic?kind=pyramid")
        group = _only(doc)
        assert group.Name == "librecharts-graphic:pyramid:4:vertical"
        assert lo_graphics.find(group) == graphics.Graphic("pyramid", 4, False)
        assert len(lo_graphics.labels(group)) == 4
        top, bottom = _top_and_bottom_width(group)  # the first step widens downwards
        assert top < bottom

        uno_command(ctx, doc, ".uno:Undo")
        assert lo_graphics.all_graphics(doc) == []
    finally:
        doc.close(True)


def test_the_inverted_pyramid_command_marks_the_group_as_inverted(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertGraphic?kind=pyramid&inverted=true")
        group = _only(doc)
        assert group.Name == "librecharts-graphic:pyramid:4:inverted"
        assert lo_graphics.find(group) == graphics.Graphic("pyramid", 4, False, inverted=True)
        assert len(lo_graphics.labels(group)) == 4
        top, bottom = _top_and_bottom_width(group)  # the first step narrows downwards
        assert top > bottom
    finally:
        doc.close(True)


def test_a_process_graphic_takes_its_steps_and_labels(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(
            ctx,
            doc,
            "org.librecharts:InsertGraphic?kind=process&steps=3&text1=A&text2=B&text3=C",
        )
        group = _only(doc)
        assert group.Name == "librecharts-graphic:process:3:horizontal"
        assert lo_graphics.labels(group) == ("A", "B", "C")
    finally:
        doc.close(True)
