"""M25: table and 2x2 matrix charts."""

from __future__ import annotations

from dataclasses import replace

import pytest

from librecharts.core import matrix, table
from librecharts.core.datasheet import sample_matrix_state, sample_table_state, state_from_table
from librecharts.core.layout.chart import layout_chart
from librecharts.core.layout.matrix import layout_matrix
from librecharts.core.layout.table import layout_table
from librecharts.core.model import MatrixSpec, TableSpec
from librecharts.core.primitives import Marker, Polyline, Rect, Text
from librecharts.core.state_io import from_json, to_json


def test_typed_cells_and_escaping() -> None:
    state = state_from_table(
        "table",
        "stacked",
        [
            ["", "Number", "Harvey", "Check", "Spark"],
            ["Row", 12, "{harvey:75}", "{check:tick}", "{spark:1,3,2}"],
            ["Escaped", "{{literal}", "{check:cross}", "{check:empty}", "text"],
        ],
    )
    data = table.parse(state)
    assert data.cells[1][1].kind == "number"
    assert data.cells[1][2].kind == "harvey"
    assert data.cells[2][1].text == "{literal}"
    assert data.cells[1][4].spark == (1.0, 3.0, 2.0)
    with pytest.raises(ValueError, match="Harvey"):
        table.parse(state_from_table("table", "stacked", [["", "A"], ["Row", "{harvey:42}"]]))


def test_column_widths_are_normalised() -> None:
    assert table.column_widths(TableSpec(), 4) == (0.25, 0.25, 0.25, 0.25)
    assert table.column_widths(TableSpec(widths=(1, 3)), 2) == (0.25, 0.75)
    assert table.column_widths(TableSpec(widths=(2,)), 2) == (0.5, 0.5)


def test_a_table_draws_cells_borders_text_and_markers() -> None:
    data = table.parse(sample_table_state())
    primitives = layout_table(data, 8000, 6000)
    assert len([p for p in primitives if isinstance(p, Rect)]) == 16
    assert any(isinstance(p, Text) and p.text == "Revenue" for p in primitives)
    assert any(isinstance(p, Polyline) for p in primitives)  # sparkline or check mark


def test_a_table_heatmap_uses_the_number_range() -> None:
    state = replace(sample_table_state(), table=TableSpec(heatmap=True))
    primitives = layout_table(table.parse(state), 8000, 6000)
    fills = {p.series for p in primitives if isinstance(p, Rect)}
    assert len(fills) > 1


def test_a_matrix_point_needs_x_and_y() -> None:
    state = state_from_table("matrix", "stacked", [["Item", "X", "Y"], ["A", None, 3], ["B", 2, 4]])
    data = matrix.parse(state)
    assert len(data.points) == 1
    assert data.points[0].label == "B"


def test_a_matrix_draws_quadrant_lines_and_points() -> None:
    spec = MatrixSpec(
        x_title="Cost",
        y_title="Value",
        quadrants=("TL", "TR", "BL", "BR"),
        labels=True,
    )
    state = replace(sample_matrix_state(), matrix=spec)
    primitives = layout_matrix(matrix.parse(state), 8000, 6000)
    assert len([p for p in primitives if isinstance(p, Marker)]) == 4
    texts = [p.text for p in primitives if isinstance(p, Text)]
    assert "TL" in texts
    assert "Cost" in texts


def test_table_and_matrix_specs_round_trip_and_validate() -> None:
    table_state = replace(sample_table_state(), table=TableSpec(zebra=True, widths=(1, 2, 3, 4)))
    assert from_json(to_json(table_state)).table == table_state.table
    matrix_state = replace(
        sample_matrix_state(), matrix=MatrixSpec(x_title="X", quadrants=("a", "b", "c", "d"))
    )
    assert from_json(to_json(matrix_state)).matrix == matrix_state.matrix
    with pytest.raises(ValueError, match="table options"):
        replace(sample_table_state(), kind="column")
    with pytest.raises(ValueError, match="cannot be sorted"):
        replace(sample_table_state(), sort="descending")
    with pytest.raises(ValueError, match="four quadrant"):
        MatrixSpec(quadrants=("a",))  # pyright: ignore[reportArgumentType]


def test_both_new_kinds_are_layout_output() -> None:
    assert layout_chart(sample_table_state(), 4000, 3000)
    assert layout_chart(sample_matrix_state(), 4000, 3000)
