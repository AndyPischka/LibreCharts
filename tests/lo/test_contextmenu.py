# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The LibreCharts submenu in the context menu of a selected chart, driven by mouse and keys.

Needs a visible document for real input events; skipped on headless Linux. The menu's contents
are tested in tests/core/test_menu.py, its commands in test_annotations.py.
"""

import time

import uno
from helpers import (
    close_datasheets,
    datasheets,
    dispatch,
    first_page,
    new_impress,
    skip_on_headless_linux,
)

from librecharts.lo import store

DOWN, RIGHT, RETURN = 1024, 1027, 1280  # com.sun.star.awt.Key
VCL_RIGHT_BUTTON = 4  # the Toolkit robot takes VCL's button codes, not awt.MouseButton


def _key(ctx, window, code):
    event = uno.createUnoStruct("com.sun.star.awt.KeyEvent")
    event.Source, event.KeyCode = window, code
    robot = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    robot.keyPress(event)
    robot.keyRelease(event)
    time.sleep(0.3)


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def test_context_menu_of_a_chart_opens_its_data_sheet(ctx):
    skip_on_headless_linux("real input events need a visible document, which aborts headless Linux")
    doc = new_impress(ctx, hidden=False)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertColumnChart")  # also attaches the menu
        group, _ = store.find_charts(first_page(doc))[0]
        controller = doc.getCurrentController()
        window = controller.getFrame().getComponentWindow()
        # Right-click on the selected chart; where exactly does not matter, the chart is large.
        size, area = window.getPosSize(), controller.VisibleArea
        click = uno.createUnoStruct("com.sun.star.awt.MouseEvent")
        click.Source, click.Buttons, click.ClickCount = window, VCL_RIGHT_BUTTON, 1
        click.X = round(
            (group.Position.X + group.Size.Width / 2 - area.X) / area.Width * size.Width
        )
        click.Y = round(
            (group.Position.Y + group.Size.Height / 2 - area.Y) / area.Height * size.Height
        )
        robot = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        robot.mousePress(click)
        robot.mouseRelease(click)
        time.sleep(0.5)
        # LibreCharts is the first entry, "Edit chart data" the first one in its submenu.
        for code in (DOWN, RIGHT, RETURN):
            _key(ctx, window, code)
        _wait_for(lambda: len(datasheets(ctx)) == 1)
    finally:
        close_datasheets(ctx)
        doc.close(True)
