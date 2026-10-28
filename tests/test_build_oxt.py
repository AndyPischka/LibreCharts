import re
import zipfile
from pathlib import Path

from build_oxt import ROOT, build


def test_oxt_contains_everything_the_manifest_references(tmp_path: Path) -> None:
    with zipfile.ZipFile(build(out_dir=tmp_path)) as oxt:
        names = set(oxt.namelist())
        manifest = oxt.read("META-INF/manifest.xml").decode()

    for referenced in re.findall(r'manifest:full-path="([^"]+)"', manifest):
        assert referenced in names
    assert "librecharts/core/scale.py" in names
    assert "LICENSE" in names


def test_version_is_taken_from_pyproject(tmp_path: Path) -> None:
    with zipfile.ZipFile(build(out_dir=tmp_path)) as oxt:
        description = oxt.read("description.xml").decode()
    assert "@VERSION@" not in description
    assert re.search(r'<version value="\d+\.\d+\.\d+"/>', description)


def test_source_tree_is_untouched(tmp_path: Path) -> None:
    build(out_dir=tmp_path)
    assert "@VERSION@" in (ROOT / "extension" / "description.xml").read_text(encoding="utf-8")
