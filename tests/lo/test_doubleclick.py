# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Double-click on a chart opens its data sheet instead of entering the group.

These tests send real mouse events, which need a visible document; they are skipped on headless
Linux, where visible documents abort LibreOffice.
"""

import time

from helpers import (
    click,
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    skip_on_headless_linux,
)

from librecharts.lo import commands, store

INSERT = "org.librecharts:InsertColumnChart"
VISIBLE_ONLY = "real mouse events need a visible document, which aborts headless Linux"
DOUBLE_CLICK_GAP_S = 1.0  # longer than any double-click time


def _visible_presentation_with_a_chart(ctx):
    skip_on_headless_linux(VISIBLE_ONLY)
    doc = new_impress(ctx, hidden=False)
    dispatch(ctx, doc, INSERT)  # also registers the double-click handler, inside LibreOffice
    group, _ = store.find_charts(first_page(doc))[0]
    # Inserting selected the chart. Simulated double-clicks on a not yet selected chart lose
    # their second press (Impress starts a drag on the first); with real mouse input the first
    # click selects the chart. That path is checked by hand.
    assert commands.selected_chart(doc.getCurrentController()) is not None
    # The first click on a chart in a fresh LibreOffice keeps it busy for ~0.4 s. LibreOffice
    # counts simulated presses as a double-click by when it handles them, so the second press of a
    # cold double-click often came after the double-click time (500 ms on Windows) and the test
    # failed. A single click first warms it up; then wait so it does not pair with the next one.
    click(ctx, doc, *_centre(group))
    time.sleep(DOUBLE_CLICK_GAP_S)
    return doc, group


def _centre(shape):
    return (
        shape.Position.X + shape.Size.Width // 2,
        shape.Position.Y + shape.Size.Height // 2,
    )


def _on_a_bar(shape):
    """A point inside the first stacked column; the group's centre may fall on a gap."""
    return (
        round(shape.Position.X + shape.Size.Width * 0.3),
        round(shape.Position.Y + shape.Size.Height * 0.55),
    )


def _settle():
    time.sleep(0.8)  # give a (wrongly) scheduled data sheet time to appear


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def test_double_click_on_a_chart_opens_its_data_sheet(ctx):
    doc, group = _visible_presentation_with_a_chart(ctx)
    try:
        click(ctx, doc, *_on_a_bar(group), clicks=2)
        _wait_for(lambda: len(datasheets(ctx)) == 1)  # opened asynchronously
        # the event was swallowed: Impress did not enter the group, the chart is still selected
        assert commands.selected_chart(doc.getCurrentController()) is not None
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_single_click_does_not_open_the_data_sheet(ctx):
    doc, group = _visible_presentation_with_a_chart(ctx)
    try:
        click(ctx, doc, *_centre(group))
        _settle()
        assert datasheets(ctx) == []
    finally:
        close_datasheets(ctx)
        doc.close(True)


def test_double_click_next_to_the_chart_is_left_to_impress(ctx):
    doc, group = _visible_presentation_with_a_chart(ctx)
    try:
        x, _ = _centre(group)
        click(ctx, doc, x, group.Position.Y // 2, clicks=2)  # on the slide, above the chart
        _settle()
        assert datasheets(ctx) == []
    finally:
        close_datasheets(ctx)
        doc.close(True)
