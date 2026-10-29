"""Conventions for the UNO integration tests in tests/lo that a linter cannot express."""

import re
from pathlib import Path

LO_TESTS = Path(__file__).parent / "lo"


def test_undo_and_redo_go_through_ui_commands() -> None:
    # XUndoManager.undo()/redo() called from the test process made LibreOffice abort
    # intermittently; use helpers.uno_command(ctx, doc, ".uno:Undo") instead.
    offenders = [
        f"{path.name}:{number}"
        for path in sorted(LO_TESTS.glob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\.(undo|redo)\(\)", line) and not line.lstrip().startswith(("#", "Use"))
    ]
    assert offenders == []


def test_documents_are_closed_through_close_doc() -> None:
    # A shape released by the bridge after its document was torn down crashed LibreOffice 25.8;
    # helpers.close_doc(doc) waits for pending releases first.
    offenders = [
        f"{path.name}:{number}"
        for path in sorted(LO_TESTS.glob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\.close\(True\)", line)
        and not line.lstrip().startswith(("#", "Use"))
        and not (path.name == "helpers.py" and line.strip() == "doc.close(True)")
    ]
    assert offenders == []
