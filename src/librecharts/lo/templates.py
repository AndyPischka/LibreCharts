# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The user's chart-template folder (M27): read, list, save and delete template files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import uno

from librecharts.core import templates


def folder(ctx: Any) -> Path:
    """``<UserConfig>/librecharts/templates``; ``~/librecharts/templates`` if that fails."""
    try:
        provider = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.util.PathSettings", ctx
        )
        base = uno.fileUrlToSystemPath(provider.UserConfig)
        return Path(base) / "librecharts" / "templates"
    except Exception:
        return Path.home() / "librecharts" / "templates"


def ensure(ctx: Any) -> Path:
    path = folder(ctx)
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_templates(ctx: Any) -> list[tuple[str, Path]]:
    """``(display name, path)`` for every readable template, sorted by name."""
    found: list[tuple[str, Path]] = []
    root = folder(ctx)
    if not root.is_dir():
        return found
    for path in sorted(root.glob("*.json")):
        try:
            template = templates.from_json(path.read_text(encoding="utf-8"))
        except (OSError, templates.TemplateError):
            continue
        found.append((template.name, path))
    return found


def load(path: Path) -> templates.Template:
    return templates.from_json(path.read_text(encoding="utf-8"))


def save(ctx: Any, template: templates.Template) -> Path:
    root = ensure(ctx)
    path = root / templates.file_name(template.name)
    path.write_text(templates.to_json(template), encoding="utf-8")
    return path


def loader(ctx: Any, location: str = "") -> Any:
    """A ``core.deck`` template loader resolving a name next to the specification file, then in
    the user's template folder, then as an absolute path (M27)."""
    base = folder(ctx)
    try:
        spec = (
            Path(uno.fileUrlToSystemPath(location))
            if location.startswith("file:")
            else Path(location)
        )
        base = spec.parent if spec.name else base
    except Exception:  # no usable path: resolve against the template folder
        base = folder(ctx)

    def load(name: str) -> Any:
        candidates = [base / name, base / templates.file_name(name), folder(ctx) / name]
        candidates += [folder(ctx) / templates.file_name(name), Path(name)]
        for path in candidates:
            if path.is_file():
                return load_template(path).state
        raise FileNotFoundError(name)

    return load


def load_template(path: Path) -> templates.Template:
    return templates.from_json(path.read_text(encoding="utf-8"))


def find(ctx: Any, name: str) -> Path | None:
    """The file of the template called ``name`` (or its file name)."""
    root = folder(ctx)
    direct = root / templates.file_name(name)
    if direct.is_file():
        return direct
    for _display, path in list_templates(ctx):
        if path.stem == name or _display == name:
            return path
    return None
