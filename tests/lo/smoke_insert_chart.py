# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""UNO integration smoke test. Runs under LibreOffice's own Python, driven by scripts/test_lo.py.

Usage: python smoke_insert_chart.py <pipe-name>
Exits 0 on success, non-zero with a message on failure. Always asks LibreOffice to terminate.
"""

import contextlib
import sys
import time

import uno
from com.sun.star.beans import PropertyValue

CONNECT_TIMEOUT_S = 60


def connect(pipe: str):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    deadline = time.monotonic() + CONNECT_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"could not connect to soffice on pipe {pipe!r}")


def test_insert_chart_adds_placeholder(ctx) -> None:
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    hidden = PropertyValue()
    hidden.Name, hidden.Value = "Hidden", True
    doc = desktop.loadComponentFromURL("private:factory/simpress", "_blank", 0, (hidden,))
    try:
        controller = doc.getCurrentController()
        page = controller.getCurrentPage()
        before = page.getCount()

        url = uno.createUnoStruct("com.sun.star.util.URL")
        url.Complete = "org.librecharts:InsertChart"
        transformer = smgr.createInstanceWithContext("com.sun.star.util.URLTransformer", ctx)
        _, url = transformer.parseStrict(url)
        dispatch = controller.getFrame().queryDispatch(url, "_self", 0)
        assert dispatch is not None, (
            "no dispatch for org.librecharts:InsertChart (extension not loaded?)"
        )
        dispatch.dispatch(url, ())

        assert page.getCount() == before + 1, (
            f"expected one new shape, got {page.getCount() - before}"
        )
        assert page.getByIndex(page.getCount() - 1).String == "LibreCharts placeholder"
    finally:
        doc.close(True)


def main() -> int:
    ctx = connect(sys.argv[1])
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    try:
        test_insert_chart_adds_placeholder(ctx)
        print("OK: test_insert_chart_adds_placeholder")
        return 0
    except AssertionError as exc:
        print(f"FAILED: {exc}")
        return 1
    finally:
        with contextlib.suppress(Exception):  # connection drops while LibreOffice shuts down
            desktop.terminate()


if __name__ == "__main__":
    sys.exit(main())
