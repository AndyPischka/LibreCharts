"""The command line's arguments (M18, ADR 0028).

Pure ``argparse``, so ``--help`` works without LibreOffice and the same parser serves the launcher
(``scripts/deck.py``) and the worker (``librecharts/cli.py``). The help texts are UI strings and
come from ``core/messages.py``; ``--locale`` picks their language.
"""

from __future__ import annotations

import argparse

from librecharts.core.messages import text


def parser(locale: str = "", prog: str = "librecharts") -> argparse.ArgumentParser:
    """The command line: ``build`` fills a template, ``update`` refreshes a deck's data links."""
    root = argparse.ArgumentParser(prog=prog, description=text("cli_description", locale))
    root.add_argument("--pipe", default="", help=argparse.SUPPRESS)  # set by scripts/deck.py
    root.add_argument("--locale", default="", help=text("cli_locale", locale))
    commands = root.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help=text("cli_build", locale))
    build.add_argument("--template", required=True, help=text("cli_template", locale))
    build.add_argument("--data", required=True, help=text("cli_data", locale))
    build.add_argument("--out", required=True, help=text("cli_out", locale))

    update = commands.add_parser("update", help=text("cli_update", locale))
    update.add_argument("deck", help=text("cli_deck", locale))
    update.add_argument("--out", default="", help=text("cli_out", locale))

    # A subcommand's default would overwrite the root's value, so leave it alone when not given.
    for command in (build, update):
        command.add_argument("--locale", default=argparse.SUPPRESS, help=text("cli_locale", locale))
    return root


def argument_locale(argv: list[str]) -> str:
    """The ``--locale`` value in ``argv``, so even the help texts speak that language."""
    for index, argument in enumerate(argv):
        if argument == "--locale" and index + 1 < len(argv):
            return argv[index + 1]
        if argument.startswith("--locale="):
            return argument.partition("=")[2]
    return ""
