"""Finding and running LibreOffice: shared by scripts/test_lo.py and scripts/deck.py.

Nothing here imports ``uno``: the scripts find the binaries, the work happens in a second process
under LibreOffice's own Python.
"""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path


def exe(name: str) -> str:
    """``name`` with the platform's executable suffix."""
    return f"{name}.exe" if sys.platform == "win32" else name


def find_program_dir() -> Path:
    """The ``program`` directory of LibreOffice; raises ``SystemExit`` if there is none."""
    candidates = [
        os.environ.get("LIBREOFFICE_PROGRAM"),
        r"C:\Program Files\LibreOffice\program",
        r"C:\Program Files (x86)\LibreOffice\program",
        "/usr/lib/libreoffice/program",
        "/opt/libreoffice/program",
        *sorted(glob.glob("/opt/libreoffice*/program"), reverse=True),
        "/Applications/LibreOffice.app/Contents/MacOS",
        str(Path.home() / "Applications/LibreOffice.app/Contents/MacOS"),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / exe("soffice")).exists():
            return Path(candidate)
    raise SystemExit("LibreOffice not found; set LIBREOFFICE_PROGRAM to its 'program' directory")


def find_python(program: Path) -> Path:
    """LibreOffice's bundled Python, or the system Python that carries ``uno``.

    Windows and the archives of Linux have it next to ``soffice``; macOS keeps it in the app's
    ``Contents/Resources`` beside ``Contents/MacOS``.
    """
    for folder in (program, program.parent / "Resources"):
        for name in ("python", "python3"):
            path = folder / exe(name)
            if path.exists():
                return path
    # Distribution packages use the system Python, which has the uno module installed.
    return Path(sys.executable) if sys.platform != "win32" else program / "python.exe"


def worker_environment(program: Path) -> dict[str, str]:
    """Environment for a worker under LibreOffice's Python (Linux finds uno and its libraries)."""
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(program), env.get("PYTHONPATH")]))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            filter(None, [str(program), env.get("LD_LIBRARY_PATH")])
        )
    return env
