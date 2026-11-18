"""Command line entry point: ``python -m librecharts.cli --pipe <name> ...`` (M18, ADR 0028).

``scripts/deck.py`` starts a headless LibreOffice and runs this module under LibreOffice's Python
with the pipe it listens on. The arguments come from ``core/cli.py`` (so ``--help`` needs no
LibreOffice), the work is in ``lo/worker.py``.
"""

from __future__ import annotations

import sys

from librecharts.core import cli as core_cli
from librecharts.lo import worker


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    args = core_cli.parser(core_cli.argument_locale(arguments)).parse_args(arguments)
    if not args.pipe:
        raise SystemExit("--pipe is missing; start the command line through scripts/deck.py")
    return worker.main(args.pipe, args)


if __name__ == "__main__":
    sys.exit(main())
