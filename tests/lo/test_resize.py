# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Resizing a chart group re-lays it out for the new size instead of stretching it."""

import time

import uno
from helpers import (
    dispatch,
    first_page,
    new_impress,
    prop,
    save_and_reload,
    skip_on_headless_linux,
    uno_command,
)

from librecharts.core.layout.column import CATEGORY_BAND
from librecharts.lo import store

INSERT = "org.librecharts:InsertColumnChart"
CATEGORIES = ("2023", "2024", "2025")


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _chart(ctx, doc):
    dispatch(ctx, doc, INSERT)
    group, _ = store.find_charts(first_page(doc))[0]
    return group


def _children(group):
    return [group.getByIndex(i) for i in range(group.getCount())]


def _category_heights(group):
    return [
        c.Size.Height
        for c in _children(group)
        if c.ShapeType == "com.sun.star.drawing.TextShape" and c.String in CATEGORIES
    ]


def _geometry(group):
    return [(c.Position.X, c.Position.Y, c.Size.Width, c.Size.Height) for c in _children(group)]


def _resize(group, width, height):
    group.Size = uno.createUnoStruct("com.sun.star.awt.Size", width, height)


def _laid_out(group):
    return all(abs(h - CATEGORY_BAND) <= 1 for h in _category_heights(group))


def _close(a, b, tolerance=2):
    return len(a) == len(b) and all(
        abs(x - y) <= tolerance
        for ga, gb in zip(a, b, strict=True)
        for x, y in zip(ga, gb, strict=True)
    )


def test_resized_chart_is_laid_out_again(ctx):
    doc = new_impress(ctx)
    try:
        group = _chart(ctx, doc)
        size = group.Size
        _resize(group, size.Width, size.Height * 2)
        _wait_for(lambda: _laid_out(group))
        assert (group.Size.Width, group.Size.Height) == (size.Width, size.Height * 2)
        assert len(_category_heights(group)) == 3
    finally:
        doc.close(True)


def test_relayout_adds_no_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        group = _chart(ctx, doc)
        manager = doc.getUndoManager()
        titles = manager.getAllUndoActionTitles()
        _resize(group, group.Size.Width // 2, group.Size.Height)  # API resize: no undo by itself
        _wait_for(lambda: _laid_out(group))
        assert manager.getAllUndoActionTitles() == titles
    finally:
        doc.close(True)


def test_undo_and_redo_of_a_resize(ctx):
    doc = new_impress(ctx)
    try:
        group = _chart(ctx, doc)
        original_size = (group.Size.Width, group.Size.Height)
        original = _geometry(group)
        doc.getCurrentController().select(group)
        helper = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.DispatchHelper", ctx
        )
        helper.executeDispatch(
            doc.getCurrentController().getFrame(),
            ".uno:TransformDialog",
            "",
            0,
            (
                prop("TransformWidth", original_size[0]),
                prop("TransformHeight", original_size[1] + 6000),
            ),
        )
        _wait_for(lambda: group.Size.Height == original_size[1] + 6000 and _laid_out(group))
        resized = _geometry(group)

        uno_command(ctx, doc, ".uno:Undo")
        _wait_for(lambda: (group.Size.Width, group.Size.Height) == original_size)
        _wait_for(lambda: _close(_geometry(group), original))

        uno_command(ctx, doc, ".uno:Redo")
        _wait_for(lambda: group.Size.Height == original_size[1] + 6000)
        _wait_for(lambda: _close(_geometry(group), resized))
    finally:
        doc.close(True)


def test_charts_in_a_reloaded_presentation_are_watched(ctx):
    # Needs a visible document (document-open jobs skip hidden ones). Visible documents abort
    # LibreOffice in headless mode on Linux; this test runs on Windows.
    skip_on_headless_linux("visible documents are not stable in headless Linux")
    doc = new_impress(ctx)
    try:
        _chart(ctx, doc)
        reloaded = save_and_reload(ctx, doc, "odp", hidden=False)  # jobs skip hidden docs
        try:
            group, _ = store.find_charts(first_page(reloaded))[0]
            _resize(group, group.Size.Width, group.Size.Height * 2)
            _wait_for(lambda: _laid_out(group))
        finally:
            reloaded.close(True)
    finally:
        doc.close(True)


def test_too_small_chart_is_left_stretched_and_recovers(ctx):
    doc = new_impress(ctx)
    try:
        group = _chart(ctx, doc)
        size = group.Size
        _resize(group, 2000, 1500)  # below the minimum layout height
        time.sleep(0.5)
        assert (group.Size.Width, group.Size.Height) == (2000, 1500)
        _resize(group, size.Width, size.Height)
        _wait_for(lambda: _laid_out(group))
    finally:
        doc.close(True)
