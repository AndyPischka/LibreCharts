"""Build dist/LibreCharts-<version>.oxt from extension/, the librecharts package and LICENSE."""

from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


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
            else:
                oxt.write(path, arcname)
        for path in sorted((root / "src" / "librecharts").rglob("*.py")):
            oxt.write(path, path.relative_to(root / "src").as_posix())
        oxt.write(root / "LICENSE", "LICENSE")
    return target


if __name__ == "__main__":
    print(build())
