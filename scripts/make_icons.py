"""Draw the sidebar icons that have no hand-made PNG (16 and 26 px, no dependencies).

Run with ``uv run python scripts/make_icons.py``; it only writes missing files, so hand-made
icons are never overwritten. Shapes are given in a 0..1 square and anti-aliased by supersampling.
"""

import struct
import zlib
from collections.abc import Callable
from pathlib import Path

IMAGES = Path(__file__).resolve().parent.parent / "extension" / "images"
Color = tuple[int, int, int]
LIGHT: Color = (143, 180, 227)
MID: Color = (94, 138, 199)
GREY: Color = (96, 96, 96)
WHITE: Color = (255, 255, 255)
SS = 4

Shape = tuple[str, tuple[float, ...], Color]


def rect(x: float, y: float, w: float, h: float, c: Color = MID) -> Shape:
    return ("rect", (x, y, x + w, y + h), c)


def dot(x: float, y: float, r: float, c: Color = MID) -> Shape:
    return ("dot", (x, y, r), c)


def poly(points: list[tuple[float, float]], c: Color = MID) -> Shape:
    return ("poly", tuple(v for p in points for v in p), c)


def _inside(shape: Shape, x: float, y: float) -> bool:
    kind, v, _ = shape
    if kind == "rect":
        return v[0] <= x < v[2] and v[1] <= y < v[3]
    if kind == "dot":
        return (x - v[0]) ** 2 + (y - v[1]) ** 2 <= v[2] ** 2
    pts = list(zip(v[0::2], v[1::2], strict=True))
    result = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def render(shapes: list[Shape], size: int) -> bytes:
    rows = b""
    for py in range(size):
        rows += b"\x00"
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SS):
                for sx in range(SS):
                    x, y = (px + (sx + 0.5) / SS) / size, (py + (sy + 0.5) / SS) / size
                    for shape in reversed(shapes):  # later shapes are on top
                        if _inside(shape, x, y):
                            acc[0] += shape[2][0]
                            acc[1] += shape[2][1]
                            acc[2] += shape[2][2]
                            acc[3] += 1
                            break
            n = acc[3]
            if n:
                rows += bytes((acc[0] // n, acc[1] // n, acc[2] // n, 255 * n // (SS * SS)))
            else:
                rows += bytes(4)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9))
    return png + chunk(b"IEND", b"")


def _frame() -> list[Shape]:
    return [
        rect(0.04, 0.06, 0.92, 0.04, GREY),
        rect(0.04, 0.9, 0.92, 0.04, GREY),
        rect(0.04, 0.06, 0.04, 0.88, GREY),
        rect(0.92, 0.06, 0.04, 0.88, GREY),
    ]


def _align(edge: str, slide: bool) -> list[Shape]:
    base = _frame() if slide else []
    sizes = (0.5, 0.3, 0.4)
    colors = (MID, LIGHT, MID)
    if edge in ("left", "right", "hcenter"):
        line = {"left": 0.17, "right": 0.8, "hcenter": 0.485}[edge]
        bars = [
            rect(
                {"left": 0.21, "right": 0.79 - w, "hcenter": 0.5 - w / 2}[edge],
                0.22 + i * 0.22,
                w,
                0.14,
                colors[i],
            )
            for i, w in enumerate(sizes)
        ]
        return [*base, rect(line, 0.16, 0.03, 0.68, GREY), *bars]
    line = {"top": 0.17, "bottom": 0.8, "vcenter": 0.485}[edge]
    bars = [
        rect(
            0.22 + i * 0.22,
            {"top": 0.21, "bottom": 0.79 - h, "vcenter": 0.5 - h / 2}[edge],
            0.14,
            h,
            colors[i],
        )
        for i, h in enumerate(sizes)
    ]
    return [*base, rect(0.16, line, 0.68, 0.03, GREY), *bars]


def _distribute(axis: str, mode: str) -> list[Shape]:
    sizes = (0.14, 0.2, 0.14) if mode == "gaps" else (0.16, 0.16, 0.16)
    pos = (0.12, 0.42, 0.74) if mode == "gaps" else (0.1, 0.42, 0.74)
    if axis == "h":
        marks = [rect(0.06, 0.12, 0.03, 0.76, GREY), rect(0.91, 0.12, 0.03, 0.76, GREY)]
        items = [rect(p + 0.04, 0.3, s, 0.4) for s, p in zip(sizes, pos, strict=True)]
    else:
        marks = [rect(0.12, 0.06, 0.76, 0.03, GREY), rect(0.12, 0.91, 0.76, 0.03, GREY)]
        items = [rect(0.3, p + 0.04, 0.4, s) for s, p in zip(sizes, pos, strict=True)]
    return [*marks, *items]


def _dumbbell() -> list[Shape]:
    shapes = [
        rect(0.2, 0.2, 0.62, 0.08, GREY),
        rect(0.2, 0.46, 0.5, 0.08, GREY),
        rect(0.2, 0.72, 0.4, 0.08, GREY),
    ]
    for y, end in ((0.24, 0.82), (0.5, 0.7), (0.76, 0.6)):
        shapes += [dot(0.2, y, 0.1, LIGHT), dot(end, y, 0.1)]
    return shapes


def _bullet() -> list[Shape]:
    shapes: list[Shape] = []
    for y, bar, mark in ((0.16, 0.5, 0.7), (0.41, 0.65, 0.82), (0.66, 0.35, 0.52)):
        shapes += [
            rect(0.1, y, 0.8, 0.18, LIGHT),
            rect(0.1, y + 0.04, bar, 0.1),
            rect(mark, y - 0.02, 0.04, 0.22, GREY),
        ]
    return shapes


def _boxplot() -> list[Shape]:
    shapes: list[Shape] = []
    for x, top, bottom, box_top, box_bottom in (
        (0.2, 0.1, 0.9, 0.26, 0.74),
        (0.58, 0.2, 0.88, 0.32, 0.68),
    ):
        middle = (box_top + box_bottom) / 2
        shapes += [
            rect(x + 0.08, top, 0.04, bottom - top, GREY),
            rect(x, box_top, 0.2, box_bottom - box_top, LIGHT),
            rect(x, middle - 0.025, 0.2, 0.05, MID),
        ]
    return shapes


def _gap() -> list[Shape]:
    """Two column groups with a dashed marker in the category gap between them."""
    return [
        rect(0.04, 0.88, 0.92, 0.04, GREY),
        rect(0.06, 0.44, 0.17, 0.44),
        rect(0.27, 0.24, 0.17, 0.64, LIGHT),
        rect(0.56, 0.34, 0.17, 0.54, LIGHT),
        rect(0.77, 0.52, 0.17, 0.36),
        *(rect(0.485, y, 0.03, 0.1, GREY) for y in (0.12, 0.32, 0.52, 0.72)),
    ]


def _bracket() -> list[Shape]:
    """Three columns under a group bracket with a stem for its label."""
    return [
        rect(0.04, 0.88, 0.92, 0.04, GREY),
        rect(0.1, 0.6, 0.22, 0.28),
        rect(0.39, 0.44, 0.22, 0.44, LIGHT),
        rect(0.68, 0.52, 0.22, 0.36),
        rect(0.1, 0.22, 0.8, 0.05, GREY),
        rect(0.1, 0.22, 0.05, 0.14, GREY),
        rect(0.85, 0.22, 0.05, 0.14, GREY),
        rect(0.475, 0.06, 0.05, 0.16, GREY),
    ]


ICONS: dict[str, Callable[[], list[Shape]]] = {
    "gap": _gap,
    "bracket": _bracket,
    "insert_dumbbell": _dumbbell,
    "insert_bullet": _bullet,
    "insert_funnel": lambda: [
        rect(0.1, 0.14, 0.8, 0.18),
        rect(0.2, 0.38, 0.6, 0.18),
        rect(0.32, 0.62, 0.36, 0.18, LIGHT),
        rect(0.42, 0.84, 0.16, 0.08, LIGHT),
    ],
    "insert_boxplot": _boxplot,
    "insert_table": lambda: [
        rect(0.1, 0.14, 0.8, 0.18),
        rect(0.1, 0.36, 0.8, 0.16, LIGHT),
        rect(0.1, 0.56, 0.8, 0.16, LIGHT),
        rect(0.1, 0.76, 0.8, 0.12, LIGHT),
        rect(0.36, 0.14, 0.03, 0.74, WHITE),
        rect(0.64, 0.14, 0.03, 0.74, WHITE),
    ],
    "insert_matrix": lambda: [
        rect(0.1, 0.1, 0.03, 0.8, GREY),
        rect(0.1, 0.87, 0.8, 0.03, GREY),
        rect(0.2, 0.14, 0.32, 0.32, LIGHT),
        rect(0.56, 0.14, 0.32, 0.32),
        rect(0.2, 0.5, 0.32, 0.32),
        rect(0.56, 0.5, 0.32, 0.32, LIGHT),
    ],
    "insert_process": lambda: [
        rect(0.04, 0.34, 0.24, 0.32),
        rect(0.38, 0.34, 0.24, 0.32, LIGHT),
        rect(0.72, 0.34, 0.24, 0.32),
        rect(0.28, 0.47, 0.1, 0.06, GREY),
        rect(0.62, 0.47, 0.1, 0.06, GREY),
    ],
    "insert_chevron": lambda: [
        poly([(0.02, 0.3), (0.26, 0.3), (0.38, 0.5), (0.26, 0.7), (0.02, 0.7), (0.14, 0.5)]),
        poly([(0.34, 0.3), (0.58, 0.3), (0.7, 0.5), (0.58, 0.7), (0.34, 0.7), (0.46, 0.5)], LIGHT),
        poly([(0.66, 0.3), (0.9, 0.3), (1.0, 0.5), (0.9, 0.7), (0.66, 0.7), (0.78, 0.5)]),
    ],
    "insert_pyramid": lambda: [
        poly([(0.5, 0.1), (0.64, 0.38), (0.36, 0.38)], LIGHT),
        poly([(0.34, 0.43), (0.66, 0.43), (0.8, 0.68), (0.2, 0.68)]),
        poly([(0.18, 0.73), (0.82, 0.73), (0.94, 0.92), (0.06, 0.92)], LIGHT),
    ],
    "insert_pyramid_inverted": lambda: [
        poly([(0.06, 0.1), (0.94, 0.1), (0.82, 0.29), (0.18, 0.29)], LIGHT),
        poly([(0.2, 0.34), (0.8, 0.34), (0.66, 0.59), (0.34, 0.59)]),
        poly([(0.36, 0.64), (0.64, 0.64), (0.5, 0.92)], LIGHT),
    ],
    "insert_icon": lambda: [
        poly(
            [
                (0.5, 0.06),
                (0.62, 0.37),
                (0.95, 0.4),
                (0.7, 0.61),
                (0.78, 0.94),
                (0.5, 0.76),
                (0.22, 0.94),
                (0.3, 0.61),
                (0.05, 0.4),
                (0.38, 0.37),
            ]
        )
    ],
}
for _axis in ("h", "v"):
    for _mode in ("gaps", "centres"):
        ICONS[f"arrange_distribute_{_axis}_{_mode}"] = lambda a=_axis, m=_mode: _distribute(a, m)
for _edge in ("left", "right", "top", "bottom", "hcenter", "vcenter"):
    ICONS[f"arrange_align_{_edge}"] = lambda e=_edge: _align(e, False)
    ICONS[f"arrange_align_slide_{_edge}"] = lambda e=_edge: _align(e, True)


def main() -> None:
    for name, build in ICONS.items():
        shapes = build()
        for size in (16, 26):
            path = IMAGES / f"{name}_{size}.png"
            if not path.exists():
                path.write_bytes(render(shapes, size))
                print("wrote", path.name)


if __name__ == "__main__":
    main()
