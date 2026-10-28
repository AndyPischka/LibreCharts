# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Shared helpers for UNO integration tests (run under LibreOffice's Python)."""

import sys
import tempfile
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue

FILTERS = {"odp": "impress8", "pptx": "Impress MS PowerPoint 2007 XML"}


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def desktop(ctx):
    return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)


def new_impress(ctx, hidden=True):
    """An empty presentation; the caller closes it.

    Keep test documents hidden where possible: in headless mode LibreOffice 26.8 intermittently
    aborts when a *visible* Calc window is closed, and visible documents abort LibreOffice in
    headless Linux. Only tests that need real mouse input use ``hidden=False``.
    """
    args = (prop("Hidden", True),) if hidden else ()
    doc = desktop(ctx).loadComponentFromURL("private:factory/simpress", "_blank", 0, args)
    page = doc.getCurrentController().getCurrentPage()
    while page.getCount():
        page.remove(page.getByIndex(0))
    return doc


def dispatch(ctx, doc, command):
    """Dispatch a LibreCharts command like the menu does."""
    url = uno.createUnoStruct("com.sun.star.util.URL")
    url.Complete = command
    transformer = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.util.URLTransformer", ctx
    )
    _, url = transformer.parseStrict(url)
    handler = doc.getCurrentController().getFrame().queryDispatch(url, "_self", 0)
    assert handler is not None, f"no dispatch for {command} (extension not loaded?)"
    handler.dispatch(url, ())


def save_and_reload(ctx, doc, fmt, hidden=True):
    """Store ``doc`` as ``fmt`` in a temp dir and load it again; the caller closes it.

    ``hidden=False`` is needed where document-open jobs matter: LibreOffice runs them for visible
    documents only.
    """
    path = Path(tempfile.mkdtemp(prefix="librecharts_")) / f"roundtrip.{fmt}"
    url = uno.systemPathToFileUrl(str(path))
    doc.storeToURL(url, (prop("FilterName", FILTERS[fmt]),))
    args = (prop("Hidden", True),) if hidden else ()
    return desktop(ctx).loadComponentFromURL(url, "_blank", 0, args)


def first_page(doc):
    return doc.getDrawPages().getByIndex(0)


def datasheets(ctx):
    """All open LibreCharts data sheets (Calc documents whose window title says so)."""
    found = []
    components = desktop(ctx).getComponents().createEnumeration()
    while components.hasMoreElements():
        component = components.nextElement()
        if not component.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
            continue
        title = component.getCurrentController().getFrame().Title
        if title.startswith("LibreCharts"):
            found.append(component)
    return found


def close_datasheets(ctx):
    for calc in datasheets(ctx):
        calc.close(True)


def uno_command(ctx, doc, command):
    """Run a LibreOffice UI command such as ``.uno:Undo`` like the menu or keyboard does.

    Use this instead of ``doc.getUndoManager().undo()/redo()``: called from this test process,
    those run on a bridge thread inside LibreOffice and made it abort intermittently while the
    extension's resize watcher was active. Users trigger undo through the UI command.
    """
    helper = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    helper.executeDispatch(doc.getCurrentController().getFrame(), command, "", 0, ())


class Skip(Exception):
    """Raised by a test that cannot run in this environment; the runner reports it as SKIP."""


def skip_on_headless_linux(reason):
    if sys.platform.startswith("linux"):
        raise Skip(reason)


def click(ctx, doc, x, y, clicks=1):
    """Click the left mouse button ``clicks`` times near document position (``x``, ``y``).

    Coordinates are in 1/100 mm on the slide, mapped to pixels through the view's visible area.
    The mapping is only rough (ADR 0010), so aim at large shapes such as a whole chart. Needs a
    *visible* ``doc``. LibreOffice counts double-clicks itself from the timing of the presses (the
    event's own ClickCount is ignored), so a double-click is two quick clicks.
    """
    controller = doc.getCurrentController()
    window = controller.getFrame().getComponentWindow()
    size, area = window.getPosSize(), controller.VisibleArea
    event = uno.createUnoStruct("com.sun.star.awt.MouseEvent")
    event.Source, event.Buttons, event.ClickCount = window, 1, 1
    event.X = round((x - area.X) / area.Width * size.Width)
    event.Y = round((y - area.Y) / area.Height * size.Height)
    robot = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    for _ in range(clicks):
        robot.mousePress(event)
        robot.mouseRelease(event)
