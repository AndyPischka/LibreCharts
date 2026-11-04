"""Import Gantt data from CSV and project files (M17).

CSV files are read by header (English or German names) or, without a header, by column position
like the data sheet. ProjectLibre `.pod` files and MS Project MSPDI `.xml` files are read from
their embedded MSPDI document; only task names, dates, notes and the base calendar are used.
Everything here is plain Python, so the mapping is tested without LibreOffice.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, replace
from datetime import date, timedelta
from xml.etree import ElementTree

from librecharts.core.gantt import END, PHASE, REMARK, START, serial, to_date
from librecharts.core.model import Calendar, ChartState
from librecharts.core.value_line import check_date

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 5000
MAX_HOLIDAYS = 1000
MAX_BARS = 10  # bar pairs per row, including the first one
_MAX_REMARK = 80

_CSV_SEPARATORS = (",", ";", "\t")
_ALIASES: dict[str, frozenset[str]] = {
    "label": frozenset(
        {"label", "activity", "task", "name", "task name", "aufgabe", "vorgang", "bezeichnung"}
    ),
    "start": frozenset({"start", "begin", "from", "anfang", "beginn", "startdatum"}),
    "end": frozenset({"end", "finish", "to", "ende", "enddatum", "fertigstellung"}),
    "remark": frozenset(
        {
            "remark",
            "note",
            "notes",
            "comment",
            "resource",
            "responsible",
            "bemerkung",
            "notiz",
            "ressource",
            "verantwortlich",
        }
    ),
    "phase": frozenset({"phase", "marker", "summary", "group", "gruppe"}),
}
_PAIR = re.compile(r"^(start|begin|anfang|beginn|end|finish|ende)\s*(\d+)$")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ].*)?")
_START_NAMES = frozenset({"start", "begin", "anfang", "beginn"})
_END_NAMES = frozenset({"end", "finish", "ende"})


class GanttImportError(Exception):
    """The file cannot be imported; ``key`` is the message key."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass(frozen=True, slots=True)
class ImportedRow:
    """One row of an imported file, before it becomes a data sheet row."""

    label: str
    start: date | None
    end: date | None
    remark: str = ""
    phase: bool = False
    extra: tuple[tuple[date, date], ...] = ()
    level: int = 0


@dataclass(frozen=True, slots=True)
class Table:
    rows: tuple[ImportedRow, ...]


def parse_csv(text: str, language: str = "en") -> Table:
    """Read a CSV table as Gantt rows.

    The separator is the comma, semicolon or tab that occurs most often in the first line. A first
    row with known column names (English or German) is used as a header; without one, the columns
    are read like the data sheet (label, start, end, remark, phase, start 2, end 2, ...).
    """
    if len(text) > MAX_BYTES:
        raise GanttImportError("import_too_large")
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines:
        return Table(())
    delimiter = max(_CSV_SEPARATORS, key=lambda separator: lines[0].count(separator))
    reader = csv.reader(
        io.StringIO(text), delimiter=delimiter, quotechar='"', skipinitialspace=True
    )
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return Table(())
    header = _header(rows[0])
    data = rows[1:] if header is not None else rows
    columns = header or _positional()
    if len(data) > MAX_ROWS:
        raise GanttImportError("import_too_many_rows")
    imported = tuple(
        row for cells in data if (row := _row_from_cells(cells, columns, language)) is not None
    )
    return Table(imported)


def _header(cells: list[str]) -> dict[str, int] | None:
    """The column indices named by ``cells``, or ``None`` if the row is not a header."""
    found: dict[str, int] = {}
    for index, cell in enumerate(cells):
        name = " ".join(cell.strip().lower().split())
        for role, aliases in _ALIASES.items():
            if name in aliases:
                found.setdefault(role, index)
                break
        else:
            match = _PAIR.fullmatch(name)
            if match is not None:
                kind, number = match.groups()
                role = "start" if kind in _START_NAMES else "end"
                found.setdefault(f"{role}{number}", index)
    if not any(key in found for key in ("label", "start", "end")) and not any(
        key.startswith(("start", "end")) for key in found
    ):
        return None
    return found


def _positional() -> dict[str, int]:
    """The data sheet's columns: label, start, end, remark, phase, then further bar pairs."""
    columns = {"label": 0, "start": START, "end": END, "remark": REMARK, "phase": PHASE}
    for number in range(2, MAX_BARS + 1):
        columns[f"start{number}"] = PHASE + 1 + 2 * (number - 2)
        columns[f"end{number}"] = PHASE + 2 + 2 * (number - 2)
    return columns


def _row_from_cells(cells: list[str], columns: dict[str, int], language: str) -> ImportedRow | None:
    def cell(role: str) -> str:
        index = columns.get(role)
        return cells[index].strip() if index is not None and index < len(cells) else ""

    label, remark, phase = cell("label"), cell("remark"), bool(cell("phase"))
    start, end = _date(cell("start"), language), _date(cell("end"), language)
    if start is None and end is not None:
        start = end
    elif end is None and start is not None:
        end = start
    if start is not None and end is not None and end < start:
        start, end = end, start
    extra: list[tuple[date, date]] = []
    for number in range(2, MAX_BARS + 1):
        first, second = (
            _date(cell(f"start{number}"), language),
            _date(cell(f"end{number}"), language),
        )
        if first is None or second is None:
            continue
        extra.append((second, first) if second < first else (first, second))
    if not label and not remark and start is None and not extra and not phase:
        return None
    return ImportedRow(label, start, end, remark, phase, tuple(extra))


def _date(text: str, language: str) -> date | None:
    """A date as the data sheet or a project file writes it; ``None`` if it is not one."""
    text = text.strip()
    if not text:
        return None
    if _ISO.fullmatch(text):
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    checked = check_date(text, language)
    if not isinstance(checked, str):
        return to_date(checked)
    try:
        return to_date(float(text))
    except ValueError:
        return None


def parse_msppi(data: bytes, language: str = "en") -> Table:
    """Read the tasks of an MSPDI XML document or a ProjectLibre `.pod` that embeds one."""
    root = _project(data)
    rows: list[ImportedRow] = []
    for task in _elements(root, "Task"):
        row = _task_row(task, language)
        if row is not None:
            rows.append(row)
    if len(rows) > MAX_ROWS:
        raise GanttImportError("import_too_many_rows")
    return Table(tuple(rows))


def _task_row(task: ElementTree.Element, language: str) -> ImportedRow | None:
    if _int(task, "UID") == 0 or _int(task, "ID") == 0:
        return None
    if _int(task, "Active") == 0:
        return None
    name = _text(task, "Name")
    start = _date(_text(task, "Start"), language)
    finish = _date(_text(task, "Finish"), language)
    notes_text = _text(task, "Notes")
    notes = notes_text.splitlines()[0].strip()[:_MAX_REMARK] if notes_text else ""
    level = _int(task, "OutlineLevel") or 0
    label = "  " * max(level - 1, 0) + name
    if _int(task, "Summary") == 1:
        return ImportedRow(label, start, finish, notes, True, (), level)
    if _int(task, "Milestone") == 1 or (
        start is not None and finish is not None and start == finish
    ):
        day = start or finish
        return ImportedRow(label, day, day, notes, False, (), level)
    if start is not None or finish is not None:
        start, finish = start or finish, finish or start
        if start is not None and finish is not None and finish < start:
            start, finish = finish, start
        return ImportedRow(label, start, finish, notes, False, (), level)
    if not label and not notes:
        return None
    return ImportedRow(label, None, None, notes, False, (), level)


def calendar_from_msppi(data: bytes) -> Calendar | None:
    """The base calendar of an MSPDI project, or ``None`` if it has no working week."""
    root = _project(data)
    base = _int(root, "BaseCalendarUID") or 1
    calendars = _elements(root, "Calendar")
    chosen = next((item for item in calendars if _int(item, "UID") == base), None)
    if chosen is None:
        chosen = calendars[0] if calendars else None
    if chosen is None:
        return None
    working: list[int] = []
    for weekday in _elements(chosen, "WeekDay"):
        day_type = _int(weekday, "DayType")
        if day_type is None or not 1 <= day_type <= 7:
            continue
        if _int(weekday, "DayWorking") == 0:
            continue
        working.append((day_type + 5) % 7)  # MSPDI: 1 = Sunday, 2 = Monday, ...
    if not working:
        return None
    holidays: list[date] = []
    for exception in _elements(chosen, "Exception"):
        if _int(exception, "DayWorking") == 1:
            continue  # a working exception
        period = next((child for child in exception if _local(child.tag) == "TimePeriod"), None)
        if period is None:
            continue
        first = _date(_text(period, "FromDate"), "en")
        last = _date(_text(period, "ToDate"), "en")
        if first is None or last is None:
            continue
        day = first
        while day <= last and len(holidays) < MAX_HOLIDAYS:
            holidays.append(day)
            day += timedelta(days=1)
    return Calendar(tuple(sorted(set(working))), tuple(holidays))


def state_from_table(table: Table, base: ChartState) -> ChartState:
    """``base`` with the data sheet of ``table``; annotations and moved labels are dropped."""
    extra = max((len(row.extra) for row in table.rows), default=0)
    width = PHASE + 1 + 2 * extra
    header = ["Activity", "Start", "End", "Remark", "Phase"]
    for _ in range(extra):
        header += ["Start", "End"]
    cells: list[tuple[str, ...]] = [tuple(header)]
    values: list[tuple[float | None, ...]] = [tuple(None for _ in range(width))]
    for row in table.rows:
        cell = [""] * width
        value: list[float | None] = [None] * width
        cell[0] = row.label
        if row.start is not None:
            cell[START] = str(serial(row.start))
            value[START] = float(serial(row.start))
        if row.end is not None:
            cell[END] = str(serial(row.end))
            value[END] = float(serial(row.end))
        cell[REMARK] = row.remark
        cell[PHASE] = "x" if row.phase else ""
        for index, (start, end) in enumerate(row.extra):
            start_column = PHASE + 1 + 2 * index
            cell[start_column] = str(serial(start))
            value[start_column] = float(serial(start))
            cell[start_column + 1] = str(serial(end))
            value[start_column + 1] = float(serial(end))
        cells.append(tuple(cell))
        values.append(tuple(value))
    return replace(
        base,
        cells=tuple(cells),
        values=tuple(values),
        annotations=(),
        labels=(),
        link=None,
    )


def _project(data: bytes) -> ElementTree.Element:
    payload = _msppi_bytes(data)
    if payload is None:
        raise GanttImportError("import_not_project")
    try:
        # A local file the user chose; ElementTree does not resolve external entities.
        return ElementTree.fromstring(payload)  # noqa: S314
    except ElementTree.ParseError as exc:
        raise GanttImportError("import_not_project") from exc


def _msppi_bytes(data: bytes) -> bytes | None:
    """The MSPDI XML in ``data``: a plain document, or the entry of a ProjectLibre `.pod` ZIP."""
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                total = 0
                for info in archive.infolist():
                    total += info.file_size
                    if total > MAX_BYTES:
                        raise GanttImportError("import_too_large")
                    found = _xml_part(archive.read(info))
                    if found is not None:
                        return found
        except zipfile.BadZipFile as exc:
            raise GanttImportError("import_not_project") from exc
        return None
    if len(data) > MAX_BYTES:
        raise GanttImportError("import_too_large")
    return _xml_part(data)


def _xml_part(data: bytes) -> bytes | None:
    start = data.find(b"<Project")
    if start < 0:
        start = data.find(b"<?xml")
    if start < 0:
        return None
    end = data.rfind(b"</Project>")
    if end < start:
        return None
    return data[start : end + len(b"</Project>")]


def _elements(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [element for element in root.iter() if _local(element.tag) == name]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ElementTree.Element, name: str) -> str:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _int(element: ElementTree.Element, name: str) -> int | None:
    try:
        return int(_text(element, name))
    except ValueError:
        return None
