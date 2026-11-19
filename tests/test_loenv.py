"""Finding LibreOffice and its Python on every platform (M21: macOS)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from loenv import exe, find_program_dir, find_python, worker_environment


def app(tmp_path: Path) -> Path:
    """A macOS-like LibreOffice.app: soffice in Contents/MacOS, python in Contents/Resources."""
    program = tmp_path / "LibreOffice.app" / "Contents" / "MacOS"
    program.mkdir(parents=True)
    (program / exe("soffice")).write_text("", encoding="utf-8")
    resources = program.parent / "Resources"
    resources.mkdir()
    (resources / exe("python")).write_text("", encoding="utf-8")
    return program


def test_the_environment_variable_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    program = app(tmp_path)
    monkeypatch.setenv("LIBREOFFICE_PROGRAM", str(program))
    assert find_program_dir() == program


def test_python_is_found_in_the_resources_of_a_mac_app(tmp_path: Path) -> None:
    program = app(tmp_path)
    assert find_python(program) == program.parent / "Resources" / exe("python")


def test_python_next_to_soffice_comes_first(tmp_path: Path) -> None:
    program = app(tmp_path)
    (program / exe("python")).write_text("", encoding="utf-8")
    assert find_python(program) == program / exe("python")


def test_without_a_bundled_python_the_system_python_carries_uno(tmp_path: Path) -> None:
    program = tmp_path / "program"
    program.mkdir()
    expected = Path(sys.executable) if sys.platform != "win32" else program / "python.exe"
    assert find_python(program) == expected


def test_only_linux_needs_library_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    assert "LD_LIBRARY_PATH" not in worker_environment(tmp_path)
    monkeypatch.setattr(sys, "platform", "linux")
    assert str(tmp_path) in worker_environment(tmp_path)["LD_LIBRARY_PATH"]
