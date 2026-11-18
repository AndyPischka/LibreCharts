"""Run the LibreCharts command line under LibreOffice's Python (M18, ADR 0028).

Finds LibreOffice like ``scripts/test_lo.py`` does, starts a headless soffice with a throwaway
profile on a private pipe, and runs ``python -m librecharts.cli`` against it::

    uv run poe deck build --template template.odp --data charts.json --out deck.odp
    uv run poe deck update deck.odp

The extension does not have to be installed in the profile: the worker imports ``librecharts`` from
``src``. Nothing here imports ``uno``, so ``--help`` works without LibreOffice.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHUTDOWN_TIMEOUT_S = 30

sys.path[:0] = [str(HERE), str(ROOT / "src")]

from loenv import exe, find_program_dir, find_python, worker_environment  # noqa: E402

from librecharts.core import cli  # noqa: E402
from librecharts.core.messages import text  # noqa: E402


def main() -> int:
    arguments = sys.argv[1:]
    locale = cli.argument_locale(arguments)
    cli.parser(locale).parse_args(arguments)  # --help and wrong input end here
    try:
        program = find_program_dir()
    except SystemExit:
        print(text("cli_no_libreoffice", locale), file=sys.stderr)
        return 1

    pipe = f"librecharts_{uuid.uuid4().hex[:12]}"
    env = worker_environment(program)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT / "src"), env.get("PYTHONPATH")]))
    worker = [str(find_python(program)), "-m", "librecharts.cli", "--pipe", pipe, *arguments]
    with tempfile.TemporaryDirectory(prefix="librecharts_profile_") as tmp:
        profile = f"-env:UserInstallation={Path(tmp).as_uri()}"
        soffice = subprocess.Popen(
            [
                str(program / exe("soffice")),
                profile,
                "--headless",
                "--invisible",
                "--norestore",
                f"--accept=pipe,name={pipe};urp;",
            ]
        )
        try:
            # The worker shuts LibreOffice down when it is done; only our own child is ever killed.
            return subprocess.run(worker, check=False, env=env).returncode
        finally:
            try:
                soffice.wait(timeout=SHUTDOWN_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                soffice.kill()
                soffice.wait()


if __name__ == "__main__":
    sys.exit(main())
