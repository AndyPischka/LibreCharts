"""Run the UNO integration tests in tests/lo against a real LibreOffice.

Builds the .oxt, installs it into a throwaway profile (the user's own profile is never touched),
starts a headless soffice on a private pipe and runs tests/lo/runner.py under LibreOffice's own
Python, which executes every tests/lo/test_*.py. Set LIBREOFFICE_PROGRAM to the `program`
directory to override discovery. Pass a module name (``test_automation``) to run only that one.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from build_oxt import ROOT, build
from loenv import exe, find_program_dir, find_python, worker_environment

RUNNER = ROOT / "tests" / "lo" / "runner.py"
SHUTDOWN_TIMEOUT_S = 30


def main() -> int:
    """Run every tests/lo module in its own LibreOffice and profile, so modules cannot affect
    each other."""
    only = sys.argv[1] if len(sys.argv) > 1 else None
    program = find_program_dir()
    python = find_python(program)
    env = worker_environment(program)
    oxt = build()
    listing = subprocess.run(
        [str(python), str(RUNNER), "--list"], check=True, env=env, capture_output=True, text=True
    )
    modules = [module for module in listing.stdout.split() if only in (None, module)]

    failed: list[str] = []
    for module in modules:
        print(f"=== {module}", flush=True)
        # A fresh profile per module: state that LibreOffice keeps in the profile made the mouse
        # tests of a later module miss their target.
        with tempfile.TemporaryDirectory(prefix="librecharts_profile_") as tmp:
            profile = f"-env:UserInstallation={Path(tmp).as_uri()}"
            subprocess.run([str(program / exe("unopkg")), "add", profile, str(oxt)], check=True)
            if run_module(program, python, env, profile, module) != 0:
                failed.append(module)

    print(f"=== modules failed: {', '.join(failed) or 'none'}", flush=True)
    return 1 if failed else 0


def run_module(program: Path, python: Path, env: dict[str, str], profile: str, module: str) -> int:
    pipe = f"librecharts_{uuid.uuid4().hex[:12]}"
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
        result = subprocess.run([str(python), str(RUNNER), pipe, module], check=False, env=env)
    finally:
        # The runner asks LibreOffice to terminate; only our own child is ever killed.
        try:
            soffice.wait(timeout=SHUTDOWN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            soffice.kill()
            soffice.wait()
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
