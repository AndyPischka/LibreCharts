"""2x2 matrix data sheet: points with x, y, size and group (M25)."""

from __future__ import annotations

from dataclasses import dataclass

from librecharts.core.model import ChartState, MatrixSpec


@dataclass(frozen=True, slots=True)
class MatrixPoint:
    label: str
    x: float
    y: float
    size: float | None
    group: int


@dataclass(frozen=True, slots=True)
class MatrixData:
    points: tuple[MatrixPoint, ...]
    groups: tuple[str, ...]
    spec: MatrixSpec


def changed(spec: MatrixSpec, values: dict[str, str]) -> MatrixSpec:
    """The matrix options after the dialog's fields; invalid values raise ``ValueError``."""
    from dataclasses import replace

    fields: dict[str, object] = {}
    for key in ("x_title", "y_title", "x_low", "x_high", "y_low", "y_high"):
        if key in values:
            fields[key] = values[key]
    if "quadrants" in values:
        parts = tuple(part.strip() for part in values["quadrants"].split("|"))
        if len(parts) != 4:
            raise ValueError("a matrix needs four quadrant labels")
        fields["quadrants"] = parts
    for key in ("x_split", "y_split"):
        if key in values:
            text = values[key].strip()
            fields[key] = None if not text else float(text.replace(",", "."))
    for key in ("bubbles", "labels"):
        if key in values:
            flag = {"true": True, "false": False}.get(values[key].strip().lower())
            if flag is None:
                raise ValueError(f"not a flag: {values[key]!r}")
            fields[key] = flag
    return replace(spec, **fields)  # type: ignore[arg-type]


def parse(state: ChartState) -> MatrixData:
    """Read ``Label | X | Y | Size | Group`` by column position."""
    spec = state.matrix or MatrixSpec()
    points: list[MatrixPoint] = []
    groups: list[str] = []
    for cells, values in zip(state.cells[1:], state.values[1:], strict=False):
        if len(values) < 3 or not cells or not cells[0].strip():
            continue
        if values[1] is None or values[2] is None:
            continue
        label = cells[0]
        size = values[3] if len(values) > 3 else None
        group_name = cells[4].strip() if len(cells) > 4 and cells[4] else ""
        if group_name not in groups:
            groups.append(group_name)
        points.append(
            MatrixPoint(
                label,
                float(values[1]),
                float(values[2]),
                size,
                groups.index(group_name),
            )
        )
    if spec.bubbles and any(point.size is None for point in points):
        raise ValueError("a bubble matrix needs a size for every point")
    return MatrixData(tuple(points), tuple(groups), spec)
