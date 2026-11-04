import io
import zipfile
from dataclasses import replace
from datetime import date

import pytest

from librecharts.core.datasheet import sample_gantt_state
from librecharts.core.gantt import parse_gantt, serial
from librecharts.core.gantt_import import (
    MAX_BYTES,
    MAX_ROWS,
    GanttImportError,
    ImportedRow,
    Table,
    calendar_from_msppi,
    parse_csv,
    parse_msppi,
    state_from_table,
)
from librecharts.core.model import Annotation, Calendar, LabelKey, LabelOffset

MSPDI = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <BaseCalendarUID>1</BaseCalendarUID>
  <Calendars>
    <Calendar>
      <UID>1</UID>
      <WeekDays>
        <WeekDay><DayType>1</DayType><DayWorking>0</DayWorking></WeekDay>
        <WeekDay><DayType>2</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>3</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>4</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>5</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>6</DayType><DayWorking>1</DayWorking></WeekDay>
        <WeekDay><DayType>7</DayType><DayWorking>0</DayWorking></WeekDay>
      </WeekDays>
      <Exceptions>
        <Exception>
          <TimePeriod>
            <FromDate>2026-12-25T00:00:00</FromDate>
            <ToDate>2026-12-25T23:59:59</ToDate>
          </TimePeriod>
        </Exception>
      </Exceptions>
    </Calendar>
  </Calendars>
  <Tasks>
    <Task><UID>0</UID><ID>0</ID><Name>Project</Name><Summary>1</Summary></Task>
    <Task>
      <UID>1</UID><ID>1</ID><Name>Phase</Name>
      <Start>2026-01-05T08:00:00</Start><Finish>2026-02-27T17:00:00</Finish>
      <Summary>1</Summary><OutlineLevel>1</OutlineLevel>
    </Task>
    <Task>
      <UID>2</UID><ID>2</ID><Name>Design</Name>
      <Start>2026-01-05T08:00:00</Start><Finish>2026-01-30T17:00:00</Finish>
      <Notes>Team A
more</Notes><OutlineLevel>2</OutlineLevel>
    </Task>
    <Task>
      <UID>3</UID><ID>3</ID><Name>Approved</Name>
      <Start>2026-02-27T08:00:00</Start><Finish>2026-02-27T17:00:00</Finish>
      <Milestone>1</Milestone><OutlineLevel>2</OutlineLevel>
    </Task>
    <Task><UID>4</UID><ID>4</ID><Name>Heading</Name><OutlineLevel>2</OutlineLevel></Task>
    <Task><UID>5</UID><ID>5</ID><Name>Inactive</Name><Active>0</Active></Task>
  </Tasks>
</Project>
"""


def pod(xml: str, prefix: bytes = b"") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("project.xml", prefix + xml.encode())
    return buffer.getvalue()


def test_csv_with_a_header_reads_rows_by_name() -> None:
    table = parse_csv(
        "Activity,Start,End,Remark,Phase\n"
        "Concept,2026-01-05,2026-02-27,,x\n"
        "Design,2026-01-05,2026-01-30,Team A,\n"
        "Approved,2026-02-27,,,\n"
        "Heading,,,,\n"
    )
    assert table.rows == (
        ImportedRow("Concept", date(2026, 1, 5), date(2026, 2, 27), "", True),
        ImportedRow("Design", date(2026, 1, 5), date(2026, 1, 30), "Team A"),
        ImportedRow("Approved", date(2026, 2, 27), date(2026, 2, 27)),
        ImportedRow("Heading", None, None),
    )


def test_csv_without_a_header_reads_the_data_sheet_columns() -> None:
    table = parse_csv("Concept,2026-01-05,2026-02-27,,x\n")
    assert table.rows == (ImportedRow("Concept", date(2026, 1, 5), date(2026, 2, 27), "", True),)


def test_csv_reads_semicolons_tabs_and_german_names() -> None:
    semicolon = parse_csv("Aufgabe;Beginn;Ende;Bemerkung;Phase\nKonzept;05.01.2026;27.02.2026;;x\n")
    assert semicolon.rows == (
        ImportedRow("Konzept", date(2026, 1, 5), date(2026, 2, 27), "", True),
    )
    tab = parse_csv("Task Name\tStart\tFinish\nDesign\t2026-01-05\t2026-01-30\n")
    assert tab.rows == (ImportedRow("Design", date(2026, 1, 5), date(2026, 1, 30)),)


def test_csv_reads_quoted_fields_and_iso_datetimes() -> None:
    table = parse_csv(
        "Activity,Start,End,Remark\n"
        '"Concept, phase 1",2026-01-05T08:00:00,2026-02-27T17:00:00,"A, B"\n'
    )
    assert table.rows == (
        ImportedRow("Concept, phase 1", date(2026, 1, 5), date(2026, 2, 27), "A, B"),
    )


def test_csv_reads_calc_serials_and_swaps_dates() -> None:
    table = parse_csv(f"A,{serial(date(2026, 3, 1))},{serial(date(2026, 2, 1))},,\n")
    assert table.rows == (ImportedRow("A", date(2026, 2, 1), date(2026, 3, 1)),)


def test_csv_reads_further_bar_pairs() -> None:
    table = parse_csv(
        "Activity,Start,End,Remark,Phase,Start 2,End 2\n"
        "Testing,2026-04-13,2026-05-15,,,2026-05-25,2026-06-12\n"
    )
    assert table.rows == (
        ImportedRow(
            "Testing",
            date(2026, 4, 13),
            date(2026, 5, 15),
            "",
            False,
            ((date(2026, 5, 25), date(2026, 6, 12)),),
        ),
    )


def test_csv_ignores_an_incomplete_further_pair() -> None:
    table = parse_csv(
        "Activity,Start,End,Remark,Phase,Start 2,End 2\n"
        "Testing,2026-04-13,2026-05-15,,,2026-05-25,\n"
    )
    assert table.rows[0].extra == ()


def test_an_empty_csv_has_no_rows() -> None:
    assert parse_csv("").rows == ()
    assert parse_csv("\n,,,\n").rows == ()


def test_a_csv_that_is_too_large_or_has_too_many_rows_is_rejected() -> None:
    with pytest.raises(GanttImportError, match="import_too_large"):
        parse_csv("x" * (MAX_BYTES + 1))
    with pytest.raises(GanttImportError, match="import_too_many_rows"):
        parse_csv("A,2026-01-05,2026-01-09\n" * (MAX_ROWS + 1))


def test_mspdi_reads_tasks_summaries_milestones_and_headings() -> None:
    table = parse_msppi(MSPDI.encode())
    assert [(row.label, row.start, row.end, row.phase) for row in table.rows] == [
        ("Phase", date(2026, 1, 5), date(2026, 2, 27), True),
        ("  Design", date(2026, 1, 5), date(2026, 1, 30), False),
        ("  Approved", date(2026, 2, 27), date(2026, 2, 27), False),
        ("  Heading", None, None, False),
    ]
    assert table.rows[1].remark == "Team A"
    assert table.rows[1].level == 2


def test_a_projectlibre_pod_embeds_the_mspdi_after_binary_data() -> None:
    table = parse_msppi(pod(MSPDI, b"\x00\x01java serialization"))
    assert [row.label for row in table.rows] == ["Phase", "  Design", "  Approved", "  Heading"]


def test_a_file_without_mspdi_is_rejected() -> None:
    with pytest.raises(GanttImportError, match="import_not_project"):
        parse_msppi(b"not a project")
    with pytest.raises(GanttImportError, match="import_not_project"):
        parse_msppi(pod("<Other/>"))


def test_the_base_calendar_is_read_from_mspdi() -> None:
    assert calendar_from_msppi(MSPDI.encode()) == Calendar((0, 1, 2, 3, 4), (date(2026, 12, 25),))


def test_a_project_without_a_calendar_keeps_the_chart_calendar() -> None:
    assert calendar_from_msppi(b"<Project><Tasks/></Project>") is None


def test_the_table_becomes_a_data_sheet_and_drops_annotations_and_labels() -> None:
    base = replace(
        sample_gantt_state(),
        annotations=(Annotation("value_line", 0, 0, value=1.0),),
        labels=(LabelOffset(LabelKey("total", 0), 1.0, 2.0),),
    )
    table = Table(
        (
            ImportedRow("A", date(2026, 1, 5), date(2026, 1, 9), "note", True),
            ImportedRow(
                "B",
                date(2026, 2, 2),
                date(2026, 2, 6),
                "",
                False,
                ((date(2026, 2, 9), date(2026, 2, 13)),),
            ),
        )
    )
    state = state_from_table(table, base)
    assert state.annotations == ()
    assert state.labels == ()
    assert state.link is None
    assert state.calendar == base.calendar
    assert state.cells[0] == ("Activity", "Start", "End", "Remark", "Phase", "Start", "End")
    assert state.values[1] == (
        None,
        float(serial(date(2026, 1, 5))),
        float(serial(date(2026, 1, 9))),
        None,
        None,
        None,
        None,
    )
    assert state.values[2][5] == float(serial(date(2026, 2, 9)))
    rows = parse_gantt(state).rows
    assert [(row.label, row.kind) for row in rows] == [("A", "phase"), ("B", "bar")]
    assert rows[1].marks[1].start == date(2026, 2, 9)


def test_an_empty_table_keeps_only_the_header() -> None:
    state = state_from_table(Table(()), sample_gantt_state())
    assert state.cells == (("Activity", "Start", "End", "Remark", "Phase"),)
    assert state.values == ((None, None, None, None, None),)
