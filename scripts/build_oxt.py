"""Build dist/LibreCharts-<version>.oxt from extension/, the librecharts package and LICENSE.

``extension/Addons.xcu`` carries the English and German menu titles; the build adds every further
language of ``core/locales/`` to it (M21, ADR 0031), so translators only ever edit the JSON files.
"""

from __future__ import annotations

import re
import sys
import tomllib
import zipfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from librecharts.core.messages import (  # noqa: E402
    SOURCE_LANGUAGES,
    addon_title,
    languages,
)

# An innermost <node> of Addons.xcu: one menu or toolbar entry with its Title and URL.
_ENTRY = re.compile(r"<node [^>]*>(?:(?!<node ).)*?</node>", re.DOTALL)
_URL = re.compile(r"<value>org\.librecharts:([^<]+)</value>")
_GERMAN = re.compile(r'^([ \t]*)<value xml:lang="de">[^<]*</value>\n', re.MULTILINE)


def _version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def localized_addons(text: str, extra: tuple[str, ...] | None = None) -> str:
    """``Addons.xcu`` with the titles of the ``extra`` languages added after each German one.

    A language without a translation of a title gets none; LibreOffice then shows the English one.
    """
    codes = tuple(code for code in languages() if code not in SOURCE_LANGUAGES)
    codes = codes if extra is None else extra

    def entry(match: re.Match[str]) -> str:
        block = match.group(0)
        url = _URL.search(block)
        if url is None or 'oor:name="Title"' not in block:
            return block
        command = url.group(1)

        def add(german: re.Match[str]) -> str:
            indent = german.group(1)
            lines = [german.group(0)]
            for code in codes:
                title = addon_title(command, code)
                english = addon_title(command, "en")
                if title is not None and title != english:
                    lines.append(
                        f'{indent}<value xml:lang="{code}">{escape(title, quote=False)}</value>\n'
                    )
            return "".join(lines)

        return _GERMAN.sub(add, block, count=1)

    return _ENTRY.sub(entry, text)


def build(root: Path = ROOT, out_dir: Path | None = None) -> Path:
    version = _version(root)
    out_dir = out_dir or root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"LibreCharts-{version}.oxt"

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as oxt:
        for path in sorted((root / "extension").rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            arcname = path.relative_to(root / "extension").as_posix()
            if arcname == "description.xml":
                text = path.read_text(encoding="utf-8").replace("@VERSION@", version)
                oxt.writestr(arcname, text)
            elif arcname == "Addons.xcu":
                oxt.writestr(arcname, localized_addons(path.read_text(encoding="utf-8")))
            else:
                oxt.write(path, arcname)
        package = root / "src" / "librecharts"
        for path in sorted([*package.rglob("*.py"), *package.rglob("locales/*.json")]):
            if "__pycache__" not in path.parts:
                oxt.write(path, path.relative_to(root / "src").as_posix())
        oxt.write(root / "LICENSE", "LICENSE")
    return target


if __name__ == "__main__":
    print(build())
