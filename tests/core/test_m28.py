"""M28: importing CSV and spreadsheet data into a chart."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import importdata
from librecharts.core.datasheet import sample_state
from librecharts.core.model import Link
from librecharts.core.state_io import from_json, to_json


def test_csv_is_read_with_semicolons_or_tabs() -> None:
    assert importdata.table("A;B\n1;2") == [["A", "B"], ["1", "2"]]
    assert importdata.table("A\tB\n1\t2") == [["A", "B"], ["1", "2"]]
    assert importdata.table('A,B\n"x, y",2') == [["A", "B"], ["x, y", "2"]]


def test_import_replaces_cells_and_values() -> None:
    state = importdata.state_with_table(sample_state(), [["", "2024"], ["A", "3,5"]])
    assert state.cells == (("", "2024"), ("A", "3,5"))
    assert state.values == ((None, 2024.0), (None, 3.5))


def test_an_auto_updating_link_round_trips() -> None:
    state = replace(
        sample_state(),
        link=Link("file:///x.ods", "Sheet1", "A1:B2", auto=True),
    )
    restored = from_json(to_json(state)).link
    assert restored is not None
    assert restored.auto is True


def test_empty_and_too_small_tables_are_refused() -> None:
    with pytest.raises(importdata.ImportError, match="import_empty"):
        importdata.table("\n \n")
    with pytest.raises(importdata.ImportError, match="import_too_small"):
        importdata.state_with_table(sample_state(), [["A"]])
