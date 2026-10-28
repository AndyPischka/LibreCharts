# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Minimal test runner for UNO integration tests. Runs under LibreOffice's own Python.

Started by scripts/test_lo.py: ``python runner.py <pipe-name>``. Connects to the soffice listening
on that pipe, calls every ``test_*(ctx)`` function of every ``tests/lo/test_*.py`` module in file
order, prints PASS/FAIL per test, then always asks LibreOffice to terminate.
"""

import contextlib
import importlib
import inspect
import sys
import time
import traceback
from pathlib import Path

import uno

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent.parent / "src")]

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


def collect():
    for path in sorted(HERE.glob("test_*.py")):
        module = importlib.import_module(path.stem)
        functions = inspect.getmembers(module, inspect.isfunction)
        for name, fn in sorted(functions, key=lambda item: item[1].__code__.co_firstlineno):
            if name.startswith("test_") and fn.__module__ == module.__name__:
                yield f"{path.stem}::{name}", fn


def _alive(ctx) -> bool:
    try:
        ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    except Exception:
        return False
    return True


def main() -> int:
    ctx = connect(sys.argv[1])
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    passed = failed = 0
    try:
        for test_id, fn in collect():
            try:
                fn(ctx)
            except Exception:
                failed += 1
                print(f"FAIL {test_id}\n{traceback.format_exc()}")
                if not _alive(ctx):
                    # Every further test would only fail on the dead connection.
                    print(f"ABORT LibreOffice is gone after {test_id}; remaining tests not run")
                    break
            else:
                passed += 1
                print(f"PASS {test_id}")
    finally:
        with contextlib.suppress(Exception):  # connection drops while LibreOffice shuts down
            desktop.terminate()
    print(f"{passed} passed, {failed} failed")
    return 1 if failed or not passed else 0


if __name__ == "__main__":
    sys.exit(main())
