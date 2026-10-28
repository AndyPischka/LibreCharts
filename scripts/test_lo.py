"""Run the UNO integration tests in tests/lo against a real LibreOffice.

Builds the .oxt, installs it into a throwaway profile (the user's own profile is never touched),
starts a headless soffice on a private pipe and runs tests/lo/runner.py under LibreOffice's own
Python, which executes every tests/lo/test_*.py. Set LIBREOFFICE_PROGRAM to the `program`
directory to override discovery.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from build_oxt import ROOT, build

RUNNER = ROOT / "tests" / "lo" / "runner.py"
SHUTDOWN_TIMEOUT_S = 30


def find_program_dir() -> Path:
    candidates = [
        os.environ.get("LIBREOFFICE_PROGRAM"),
        r"C:\Program Files\LibreOffice\program",
        r"C:\Program Files (x86)\LibreOffice\program",
        "/usr/lib/libreoffice/program",
        "/opt/libreoffice/program",
        *sorted(glob.glob("/opt/libreoffice*/program"), reverse=True),
        "/Applications/LibreOffice.app/Contents/MacOS",
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / _exe("soffice")).exists():
            return Path(candidate)
    raise SystemExit("LibreOffice not found; set LIBREOFFICE_PROGRAM to its 'program' directory")


def _exe(name: str) -> str:
    return f"{name}.exe" if sys.platform == "win32" else name


def find_python(program: Path) -> Path:
    for name in ("python", "python3"):
        path = program / _exe(name)
        if path.exists():
            return path
    # Distribution packages use the system Python, which has the uno module installed.
    return Path(sys.executable) if sys.platform != "win32" else program / "python.exe"


def runner_environment(program: Path) -> dict[str, str]:
    """Environment for the runner; on Linux the bundled Python finds uno and its libraries by it."""
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(program), env.get("PYTHONPATH")]))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            filter(None, [str(program), env.get("LD_LIBRARY_PATH")])
        )
    return env


def main() -> int:
    program = find_program_dir()
    python = find_python(program)
    oxt = build()
    pipe = f"librecharts_{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory(prefix="librecharts_profile_") as tmp:
        profile = f"-env:UserInstallation={Path(tmp).as_uri()}"
        subprocess.run([str(program / _exe("unopkg")), "add", profile, str(oxt)], check=True)

        soffice = subprocess.Popen(
            [
                str(program / _exe("soffice")),
                profile,
                "--headless",
                "--invisible",
                "--norestore",
                f"--accept=pipe,name={pipe};urp;",
            ]
        )
        try:
            result = subprocess.run(
                [str(python), str(RUNNER), pipe], check=False, env=runner_environment(program)
            )
        finally:
            # The runner asks LibreOffice to terminate; only our own child is ever killed.
            try:
                soffice.wait(timeout=SHUTDOWN_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                soffice.kill()
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
