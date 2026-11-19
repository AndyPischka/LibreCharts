"""Write the translation sources: ``locales/en.json`` and ``locales/de.json`` (M21, ADR 0031).

English and German live in ``core/messages.py``; the translation platform (Weblate) reads English
as its source and shows German as a reference. Run this after changing a message::

    uv run poe locales

A test fails while the files are out of date.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from librecharts.core.messages import LOCALES, SOURCE_LANGUAGES, source  # noqa: E402


def content(code: str) -> str:
    """The text of ``locales/<code>.json`` for a source language."""
    return json.dumps(source(code), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    for code in SOURCE_LANGUAGES:
        path = LOCALES / f"{code}.json"
        path.write_bytes(content(code).encode("utf-8"))
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
