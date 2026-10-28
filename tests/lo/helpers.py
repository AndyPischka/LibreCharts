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


def new_impress(ctx):
    """A hidden, empty presentation; the caller closes it.

    Keep test documents hidden: in headless mode LibreOffice 26.8 intermittently aborts when a
    *visible* Calc window is closed. Data sheets of hidden presentations open hidden as well.
    """
    doc = desktop(ctx).loadComponentFromURL(
        "private:factory/simpress", "_blank", 0, (prop("Hidden", True),)
    )
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
