"""Source line and free callouts of a chart (M22).

The source is a chart-level string drawn in the footer band; notes are short texts anchored at
fractions of the layout box. Both are chart content, not format: *Copy chart format* leaves them
alone. Validation and the undo step live here, so the adapter only reads and writes.
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qs

from librecharts.core.model import ChartState, Note


def changed(state: ChartState, query: str, command: str) -> ChartState:
    """``state`` after the note or source change in ``query``; one undo step.

    ``SetSource`` takes ``text=...`` (empty clears the source). ``AddNote`` takes ``text``, ``x``
    and ``y`` (fractions in 0..1); ``RemoveNote`` an ``index``; ``MoveNote`` an ``index``, ``x``
    and ``y``. Invalid arguments raise ``ValueError``.
    """
    args = {
        key: values[-1]
        for key, values in parse_qs(query, strict_parsing=True, keep_blank_values=True).items()
    }
    if command == "SetSource":
        source = args.get("text", "")
        if len(source) > 200:
            raise ValueError("the source must be at most 200 characters")
        return replace(state, source=source)
    if command == "AddNote":
        note = Note(args.get("text", ""), _number(args, "x"), _number(args, "y"))
        if len(state.notes) >= 8:
            raise ValueError("a chart has at most 8 notes")
        return replace(state, notes=(*state.notes, note))
    index = _index(args)
    if not 0 <= index < len(state.notes):
        raise ValueError(f"no note with index {index}")
    if command == "RemoveNote":
        notes = tuple(note for i, note in enumerate(state.notes) if i != index)
        return replace(state, notes=notes)
    if command == "MoveNote":
        note = state.notes[index]
        moved = Note(note.text, _number(args, "x"), _number(args, "y"))
        return replace(
            state,
            notes=tuple(moved if i == index else other for i, other in enumerate(state.notes)),
        )
    raise ValueError(f"unknown note command: {command!r}")


def _index(args: dict[str, str]) -> int:
    try:
        return int(args["index"])
    except (KeyError, ValueError) as exc:
        raise ValueError("a note command needs an index") from exc


def _number(args: dict[str, str], name: str) -> float:
    try:
        return float(args[name])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"a note needs a numeric {name}") from exc
