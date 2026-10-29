# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Arranging the selected shapes: same size, grid, swap; one undo step each."""

import uno
from helpers import close_doc, dispatch, first_page, new_impress, uno_command


def _rectangles(ctx, doc, specs):
    page = first_page(doc)
    shapes = []
    for x, y, width, height in specs:
        shape = doc.createInstance("com.sun.star.drawing.RectangleShape")
        page.add(shape)
        shape.Position = uno.createUnoStruct("com.sun.star.awt.Point", x, y)
        shape.Size = uno.createUnoStruct("com.sun.star.awt.Size", width, height)
        shapes.append(shape)
    return shapes


def _select(ctx, doc, shapes):
    collection = ctx.ServiceManager.createInstance("com.sun.star.drawing.ShapeCollection")
    for shape in shapes:
        collection.add(shape)
    doc.getCurrentController().select(collection)


def _rects(shapes):
    return [(s.Position.X, s.Position.Y, s.Size.Width, s.Size.Height) for s in shapes]


def test_same_size_uses_the_largest_and_undoes_in_one_step(ctx):
    doc = new_impress(ctx)
    try:
        specs = [(1000, 1000, 2000, 500), (5000, 1000, 1000, 1500)]
        shapes = _rectangles(ctx, doc, specs)
        _select(ctx, doc, shapes)
        dispatch(ctx, doc, "org.librecharts:Arrange?op=size")
        assert _rects(shapes) == [(1000, 1000, 2000, 1500), (5000, 1000, 2000, 1500)]
        uno_command(ctx, doc, ".uno:Undo")
        assert _rects(shapes) == specs
    finally:
        close_doc(doc)


def test_grid_and_swap(ctx):
    doc = new_impress(ctx)
    try:
        shapes = _rectangles(ctx, doc, [(0, 0, 1000, 1000), (9000, 0, 1000, 1000)])
        shapes += _rectangles(ctx, doc, [(0, 6000, 1000, 1000)])
        _select(ctx, doc, shapes)
        dispatch(ctx, doc, "org.librecharts:Arrange?op=grid&columns=2&gap=200")
        assert _rects(shapes) == [
            (0, 0, 1000, 1000),
            (1200, 0, 1000, 1000),
            (0, 1200, 1000, 1000),
        ]

        _select(ctx, doc, shapes[:2])
        dispatch(ctx, doc, "org.librecharts:Arrange?op=swap")
        assert [r[:2] for r in _rects(shapes[:2])] == [(1200, 0), (0, 0)]
    finally:
        close_doc(doc)


def test_a_chart_in_the_selection_is_laid_out_again(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertColumnChart")
        page = first_page(doc)
        chart = page.getByIndex(0)
        other = _rectangles(ctx, doc, [(0, 0, 100, 100)])[0]
        _select(ctx, doc, [chart, other])
        dispatch(ctx, doc, "org.librecharts:Arrange?op=width")
        assert chart.Size.Width == other.Size.Width
    finally:
        close_doc(doc)
