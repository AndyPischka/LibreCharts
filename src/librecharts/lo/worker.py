# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The command line's UNO side: connect to LibreOffice, build or update, save (M18, ADR 0028).

Started by ``librecharts/cli.py`` as ``python -m librecharts.cli --pipe <name> ...``, which
``scripts/deck.py`` runs under LibreOffice's own Python against a headless soffice it started for
the job. Exit code 0 means success, 1 a ``DeckError`` or an unreadable corporate design file
(printed with its reason), 3 a ``check`` that found deviations and did not fix them.
"""

from __future__ import annotations

import contextlib
import sys
import time
from typing import Any

import uno

from librecharts import api
from librecharts.core import designcheck as core_design
from librecharts.core import links as core_links
from librecharts.core.deck import DeckError
from librecharts.core.messages import text
from librecharts.lo import links, ui

PRESENTATION = "com.sun.star.presentation.PresentationDocument"
FILTERS = {"odp": "impress8", "pptx": "Impress MS PowerPoint 2007 XML"}
_NEVER_EXECUTE = 0  # com.sun.star.document.MacroExecMode.NEVER_EXECUTE
_NO_UPDATE = 0  # com.sun.star.document.UpdateDocMode.NO_UPDATE
CONNECT_TIMEOUT_S = 60
DEVIATIONS = 3  # exit code of a check that found deviations it did not fix


def main(pipe: str, args: Any) -> int:
    """Connect to the soffice on ``pipe``, run the parsed ``args``, then shut LibreOffice down."""
    ctx = connect(pipe)
    try:
        return run(ctx, args)
    finally:
        # This LibreOffice was started for us (scripts/deck.py) and has nothing else to do.
        with contextlib.suppress(Exception):
            _desktop(ctx).terminate()


def run(ctx: Any, args: Any) -> int:
    """Run a parsed command against the LibreOffice in ``ctx``; returns the exit code."""
    locale = args.locale or ui.ui_locale(ctx)
    try:
        if args.command == "check":
            return _check(ctx, args, locale)
        if args.command == "build":
            report = api.build_deck(ctx, args.template, args.data, args.out, locale)
        else:
            report = _update(ctx, args.deck, args.out, locale)
    except DeckError as exc:
        print(exc.message(locale), file=sys.stderr)
        return 1
    except core_design.DesignError as exc:
        print(text("design_load_failed", locale, detail=str(exc)), file=sys.stderr)
        return 1
    if report:
        print(report)
    return 0


def connect(pipe: str) -> Any:
    """The component context of the soffice listening on ``pipe``."""
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    deadline = time.monotonic() + CONNECT_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:  # LibreOffice is still starting
            time.sleep(0.5)
    raise SystemExit(f"could not connect to soffice on pipe {pipe!r}")


def _update(ctx: Any, location: str, out: str, locale: str) -> str:
    """Update the links of the deck at ``location`` and save it (as ``out`` if given)."""
    document = _load(ctx, location)
    try:
        report = api.update_links(ctx, document, None, locale)
        _save(document, out or location)
    finally:
        with contextlib.suppress(Exception):
            document.close(True)
    return report


def _check(ctx: Any, args: Any, locale: str) -> int:
    """Check the deck against the corporate design; with ``--fix`` fix it and save it."""
    document = _load(ctx, args.deck)
    try:
        result = api.check_design(document, args.design, fix=args.fix)
        print(core_design.report(result, locale, fixed=args.fix))
        if args.fix and not result.clean:
            _save(document, args.out or args.deck)
    finally:
        with contextlib.suppress(Exception):
            document.close(True)
    return 0 if result.clean or args.fix else DEVIATIONS


def _load(ctx: Any, location: str) -> Any:
    url = links.as_url(location)
    name = core_links.file_name(url)
    args = (
        ui.prop("Hidden", True),
        ui.prop("MacroExecutionMode", _NEVER_EXECUTE),
        ui.prop("UpdateDocMode", _NO_UPDATE),
    )
    try:
        document = _desktop(ctx).loadComponentFromURL(url, "_blank", 0, args)
    except Exception as exc:  # not a document, password protected, ...
        raise DeckError("deck_open_failed", name) from exc
    if document is None or not document.supportsService(PRESENTATION):
        if document is not None:
            with contextlib.suppress(Exception):
                document.close(True)
        raise DeckError("deck_open_failed", name)
    return document


def _save(document: Any, location: str) -> None:
    url = links.as_url(location)
    name = core_links.file_name(url)
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    filter_name = FILTERS.get(suffix)
    if filter_name is None:
        raise DeckError("deck_save_failed", name)
    try:
        document.storeToURL(url, (ui.prop("FilterName", filter_name), ui.prop("Overwrite", True)))
    except Exception as exc:  # e.g. the folder does not exist or is not writable
        raise DeckError("deck_save_failed", name) from exc


def _desktop(ctx: Any) -> Any:
    return ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
