"""Data links: a chart takes its data from a range of an external spreadsheet (ADR 0020).

Everything here is string and grid work, testable without LibreOffice; ``lo/links.py`` opens the
source and reads the range. A link names its source by an absolute URL and, where possible, by a
URL relative to the presentation, so that a folder with deck and workbook can be moved together.
The fetched values are stored in the chart state like data sheet values, so a linked chart draws,
copies and exports without its source.

The range is the chart's whole data sheet: its first row and first column hold the names, as in
every data sheet. It is an address (``B2:F6``) on a sheet or the name of a named range; a named
range is how a range that grows in the source (a new month) is followed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import unquote

from librecharts.core.datasheet import as_number, number_text
from librecharts.core.messages import text
from librecharts.core.model import ChartState, Link

MAX_CELLS = 10_000  # a larger range is almost certainly a mistake (a whole sheet)
MAX_COLUMNS, MAX_ROWS = 16_384, 1_048_576  # XFD1048576, the largest address in Calc and Excel
CSV_FILTER = "Text - txt - csv (StarCalc)"

_ADDRESS = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d{1,7}):\$?([A-Za-z]{1,3})\$?(\d{1,7})$")
_NAME = re.compile(
    r"[^\W\d][\w.]*"
)  # a named range: a letter or "_", then letters, digits, "_", "."
_DRIVE = re.compile(r"[A-Za-z]:")


def parse_reference(reference: str) -> tuple[str, str] | None:
    """A range as typed or pasted, as ``(sheet, address)``: ``b2:f6`` gives ``("", "B2:F6")``,
    ``Sheet1!B2:F6`` (Excel) and ``$Sheet1.$B$2:$F$6`` (Calc) give ``("Sheet1", "B2:F6")``.

    The corners may come in any order. ``None`` if ``reference`` is no such range.
    """
    reference = reference.strip()
    match = _ADDRESS.search(reference)
    if match is None:
        return None
    prefix = reference[: match.start()]
    sheet = ""
    if prefix:
        if prefix[-1] not in ".!":
            return None
        sheet = _sheet_name(prefix[:-1])
        if not sheet:
            return None
    columns = sorted((_column_index(match[1]), _column_index(match[3])))
    rows = sorted((int(match[2]), int(match[4])))
    if columns[1] >= MAX_COLUMNS or rows[0] < 1 or rows[1] > MAX_ROWS:
        return None
    return sheet, address(columns[0], rows[0] - 1, columns[1], rows[1] - 1)


def _sheet_name(prefix: str) -> str:
    """``Sheet1`` from ``$Sheet1``, ``My sheet`` from ``'My sheet'``, ``It's`` from ``'It''s'``."""
    name = prefix.removeprefix("$")
    if len(name) >= 2 and name[0] == name[-1] == "'":
        name = name[1:-1].replace("''", "'")
    return name.strip()


def address(first_column: int, first_row: int, last_column: int, last_row: int) -> str:
    """The A1 address of a range given by 0-based indices, e.g. ``(1, 1, 5, 5)`` -> ``B2:F6``."""
    return f"{_column_name(first_column)}{first_row + 1}:{_column_name(last_column)}{last_row + 1}"


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(ord("A") + rest) + name
    return name


def _column_index(name: str) -> int:
    index = 0
    for char in name.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def target(sheet: str, reference: str) -> tuple[str, str] | str:
    """Where a link should point, from the link dialog's sheet and range fields.

    ``(sheet, address)`` for an address (a sheet named in ``reference`` wins over ``sheet``),
    ``("", name)`` for a named range; else the message key of what is wrong.
    """
    reference = reference.strip()
    if not reference:
        return "link_no_range_given"
    parsed = parse_reference(reference)
    if parsed is not None:
        named, where = parsed
        chosen = named or sheet.strip()
        return (chosen, where) if chosen else "link_no_sheet_given"
    if _NAME.fullmatch(reference):
        return "", reference
    return "link_bad_range"


def check_size(rows: int, columns: int) -> str | None:
    """The message key if a range of this size cannot be a chart's data sheet, else ``None``."""
    if rows < 2 or columns < 2:
        return "link_too_small"
    if rows * columns > MAX_CELLS:
        return "link_too_large"
    return None


# URLs. Only ``file:`` URLs get a relative form; ``C:`` drives and UNC shares
# (``file://server/share``) are roots that a relative path never leaves.


def _split(url: str) -> tuple[str, list[str]] | None:
    """``(root, segments)`` of a ``file:`` URL, with ``url == root + "/" + "/".join(segments)``."""
    if not url.lower().startswith("file://"):
        return None
    authority, _, path = url[len("file://") :].partition("/")
    segments = path.split("/")
    if authority:  # UNC: the share belongs to the root
        if len(segments) < 2:
            return None
        return f"{url[: len('file://')]}{authority}/{segments[0]}", segments[1:]
    if _DRIVE.fullmatch(segments[0]):
        return f"{url[: len('file://')]}/{segments[0]}", segments[1:]
    return url[: len("file://")], segments


def _same_root(a: str, b: str) -> bool:
    return a.lower() == b.lower()  # drive letters, scheme and host ignore case


def relative_url(source: str, base: str) -> str:
    """``source`` relative to the folder of ``base``, e.g. ``data/x.xlsx`` or ``../x.xlsx``.

    Empty if the two have no common root (another drive, share or scheme) or ``base`` is empty
    (the presentation was never saved).
    """
    split_source, split_base = _split(source), _split(base)
    if split_source is None or split_base is None:
        return ""
    if not _same_root(split_source[0], split_base[0]):
        return ""
    folder, path = split_base[1][:-1], split_source[1]
    common = 0
    while common < min(len(folder), len(path) - 1) and folder[common] == path[common]:
        common += 1
    return "/".join([".."] * (len(folder) - common) + path[common:])


def resolve(relative: str, base: str) -> str:
    """The absolute URL of ``relative`` (see :func:`relative_url`) next to ``base``.

    Empty if ``base`` is no ``file:`` URL or ``relative`` climbs above the root.
    """
    split_base = _split(base)
    if split_base is None or not relative:
        return ""
    root, segments = split_base[0], split_base[1][:-1]
    for part in relative.split("/"):
        if part == "..":
            if not segments:
                return ""
            segments = segments[:-1]
        elif part not in ("", "."):
            segments = [*segments, part]
    return root + "/" + "/".join(segments)


def candidates(link: Link, presentation: str) -> tuple[str, ...]:
    """Where to look for the source, in this order: relative to the presentation (deck and
    workbook may have moved together), then the absolute URL."""
    near = resolve(link.relative, presentation) if link.relative else ""
    if near and not same_file(near, link.url):
        return near, link.url
    return (link.url,)


def same_file(a: str, b: str) -> bool:
    """Whether two URLs name the same file: percent-encoding and the case of a Windows path do
    not matter."""
    split = _split(a)
    if split is not None and split[0].lower() != "file://":  # a drive or a UNC share: Windows
        return unquote(a).lower() == unquote(b).lower()
    return unquote(a) == unquote(b)


def file_name(url: str) -> str:
    """The file name in ``url``, decoded: ``Sales 2026.xlsx``."""
    return unquote(url.rstrip("/").rsplit("/", 1)[-1])


def where(link: Link) -> str:
    """The linked range as shown to the user: ``Sheet1!B2:F6``, or a range name."""
    return f"{link.sheet}!{link.range}" if link.sheet else link.range


def describe(link: Link) -> str:
    """The source as shown to the user: ``Sales.xlsx, Sheet1!B2:F6``."""
    return f"{file_name(link.url)}, {where(link)}"


# Data.


def fetched(
    state: ChartState,
    link: Link,
    results: Sequence[Sequence[object]],
    shown: Sequence[Sequence[str]],
) -> ChartState:
    """``state`` linked by ``link``, with the data of the source range.

    ``results`` is the range read with ``getDataArray`` (floats for numbers, strings for text),
    ``shown`` the displayed text of every cell. The names in the first row and column are taken
    as the source shows them (a date header stays "Jan 2026"); every other cell holds its value,
    a number as a number and anything else as its text. The source's formulas are not kept: they
    refer to its own sheets.
    """
    cells: list[tuple[str, ...]] = []
    values: list[tuple[float | None, ...]] = []
    for r, (result_row, shown_row) in enumerate(zip(results, shown, strict=True)):
        cell_row: list[str] = []
        value_row: list[float | None] = []
        for c, (result, display) in enumerate(zip(result_row, shown_row, strict=True)):
            number = as_number(result)
            value_row.append(number)
            name = r == 0 or c == 0
            cell_row.append(display if name or number is None else number_text(number))
        cells.append(tuple(cell_row))
        values.append(tuple(value_row))
    return replace(state, cells=tuple(cells), values=tuple(values), link=link)


def view(state: ChartState) -> tuple[tuple[float | str, ...], ...]:
    """The read-only data sheet of a linked chart: numbers as numbers, names and other cells as
    text. Written with ``setDataArray``, so Calc does not reinterpret a name such as "Jan 2026"."""
    return tuple(
        tuple(
            value if value is not None and r and c else cell
            for c, (cell, value) in enumerate(zip(cell_row, value_row, strict=True))
        )
        for r, (cell_row, value_row) in enumerate(zip(state.cells, state.values, strict=True))
    )


def same_data(a: ChartState, b: ChartState) -> bool:
    """Whether an update brought nothing new: the same cells and values."""
    return a.cells == b.cells and a.values == b.values


def csv_options(first_line: str) -> str:
    """Filter options for Calc's CSV import: the separator found most often in the first line
    (comma, semicolon or tab; comma if none), double quotes, UTF-8, from line 1."""
    separator = max((",", ";", "\t"), key=first_line.count)
    return f"{ord(separator)},34,76,1"


# Messages.


def updated_text(updated: str, language: str) -> str:
    """An update time such as ``2026-10-29T14:03`` as shown in the sidebar."""
    try:
        moment = datetime.fromisoformat(updated)
    except ValueError:
        return updated
    return moment.strftime("%d.%m.%Y %H:%M" if language == "de" else "%Y-%m-%d %H:%M")


def status(link: Link, locale: str) -> str:
    """The sidebar's line about a linked chart: its source and the time of the last update."""
    if not link.updated:
        return text("status_linked", locale, source=describe(link))
    language = locale.split("-")[0].lower()
    return text(
        "status_linked_updated",
        locale,
        source=describe(link),
        time=updated_text(link.updated, language),
    )


def reason(key: str, link: Link, locale: str) -> str:
    """The message ``key`` of a link problem, filled in for ``link``."""
    return text(
        key,
        locale,
        file=file_name(link.url),
        sheet=link.sheet,
        range=link.range,
        cells=str(MAX_CELLS),
    )


@dataclass(frozen=True, slots=True)
class Problem:
    """Why one linked chart could not be updated: the message key, the chart's slide (from 1)
    and its link."""

    slide: int
    link: Link
    key: str


def report(
    count: int, changed: int, problems: Sequence[Problem], locale: str, *, single: bool = False
) -> str:
    """What to tell the user after updating: ``count`` charts read, ``changed`` of them with new
    data, ``problems`` with the charts left unchanged.

    For a single chart (``single``) only what needs saying: its problem or that nothing changed,
    and nothing if its data changed (the user sees that).
    """
    if single:
        if problems:
            return reason(problems[0].key, problems[0].link, locale)
        return "" if changed else text("link_unchanged", locale)
    if not count and not problems:
        return text("links_none", locale)
    lines: list[str] = []
    if count:
        lines.append(text("links_summary", locale, changed=str(changed), count=str(count)))
    if problems:
        lines.append(text("links_problems", locale))
        lines += [
            text("link_problem", locale, slide=str(p.slide), reason=reason(p.key, p.link, locale))
            for p in problems
        ]
    return "\n".join(lines)
