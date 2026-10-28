"""Run the UNO integration tests in tests/lo against a real LibreOffice.

Builds the .oxt, installs it into a throwaway profile (the user's own profile is never touched),
starts a headless soffice on a private pipe and runs tests/lo/smoke_insert_chart.py under
LibreOffice's own Python. Set LIBREOFFICE_PROGRAM to the `program` directory to override discovery.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from build_oxt import ROOT, build

SMOKE = ROOT / "tests" / "lo" / "smoke_insert_chart.py"
SHUTDOWN_TIMEOUT_S = 30


def find_program_dir() -> Path:
    candidates = [
        os.environ.get("LIBREOFFICE_PROGRAM"),
        r"C:\Program Files\LibreOffice\program",
        r"C:\Program Files (x86)\LibreOffice\program",
        "/usr/lib/libreoffice/program",
        "/opt/libreoffice/program",
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
    # Linux packages use the system Python, which has the uno module installed.
    return Path(sys.executable) if sys.platform != "win32" else program / "python.exe"


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
            result = subprocess.run([str(python), str(SMOKE), pipe], check=False)
        finally:
            # The smoke script asks LibreOffice to terminate; only our own child is ever killed.
            try:
                soffice.wait(timeout=SHUTDOWN_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                soffice.kill()
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
