# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Harvey balls and check marks: insert, change state, resize, reload (ADR 0021)."""

import time

import uno
from helpers import close_doc, dispatch, first_page, new_impress, save_and_reload, uno_command

from librecharts.core import elements
from librecharts.lo import elements as lo_elements


def _wait_for(condition, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        time.sleep(0.05)


def _only(doc):
    found = lo_elements.find_elements(first_page(doc))
    assert len(found) == 1
    return found[0]


def _children(group):
    return [group.getByIndex(i) for i in range(group.getCount())]


def test_insert_harvey_ball_and_change_state_in_one_undo_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertElement?harvey=50")
        group, element = _only(doc)
        assert group.Name == "librecharts-element:harvey:50%"
        assert element == elements.Element.harvey(50)
        assert len(_children(group)) == 3  # frame, outline, sector

        dispatch(ctx, doc, "org.librecharts:SetElement?harvey=0")
        group, element = _only(doc)
        assert element == elements.Element.harvey(0)
        assert len(_children(group)) == 2  # no sector

        uno_command(ctx, doc, ".uno:Undo")
        group, element = _only(doc)
        assert element == elements.Element.harvey(50)
        assert len(_children(group)) == 3
    finally:
        close_doc(doc)


def test_next_state_cycles_and_a_check_mark_ignores_ball_states(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertElement?check=tick")
        dispatch(ctx, doc, "org.librecharts:SetElement?next=1")
        assert _only(doc)[1] == elements.Element.check("cross")
        dispatch(ctx, doc, "org.librecharts:SetElement?harvey=75")  # wrong kind: no change
        assert _only(doc)[1] == elements.Element.check("cross")
    finally:
        close_doc(doc)


def test_resizing_keeps_the_ball_round(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertElement?harvey=25")
        group, _ = _only(doc)
        group.Size = uno.createUnoStruct("com.sun.star.awt.Size", 2000, 1000)

        def round_():
            _, circle, *_ = _children(_only(doc)[0])
            return abs(circle.Size.Width - circle.Size.Height) <= 2

        _wait_for(round_)
    finally:
        close_doc(doc)


def test_the_name_survives_odp_and_pptx(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, "org.librecharts:InsertElement?harvey=75")
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                assert _only(reloaded)[1] == elements.Element.harvey(75), fmt
            finally:
                close_doc(reloaded)
    finally:
        close_doc(doc)
