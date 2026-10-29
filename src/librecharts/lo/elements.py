# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Harvey balls and check marks as groups of native shapes (ADR 0021).

The state of an element is its group name (``core/elements.py``), so there is nothing to store
and nothing to claim after a copy. Every change is one undo step (``lo/undo.py``).
"""

from __future__ import annotations

from typing import Any

from librecharts.core import elements
from librecharts.core.elements import Element
from librecharts.lo import render, scheme, undo


def element_of(shape: Any) -> Element | None:
    """The element ``shape`` is, or ``None`` if it is no LibreCharts element."""
    try:
        return elements.parse(str(shape.Name))
    except AttributeError:  # e.g. a shape collection has no Name
        return None


def find_elements(page: Any) -> list[tuple[Any, Element]]:
    """All elements on ``page``, in z-order."""
    found: list[tuple[Any, Element]] = []
    for i in range(page.getCount()):
        shape = page.getByIndex(i)
        element = element_of(shape)
        if element is not None:
            found.append((shape, element))
    return found


def all_elements(doc: Any) -> list[tuple[Any, Element]]:
    """All elements on all slides of ``doc``."""
    pages = doc.getDrawPages()
    found: list[tuple[Any, Element]] = []
    for i in range(pages.getCount()):
        found.extend(find_elements(pages.getByIndex(i)))
    return found


def selected_elements(controller: Any) -> list[tuple[Any, Element]]:
    """Every selected element, including those in a multiple selection."""
    return _elements_in(controller.getSelection())


def _elements_in(selection: Any) -> list[tuple[Any, Element]]:
    if selection is None:
        return []
    element = element_of(selection)
    if element is not None:
        return [(selection, element)]
    if hasattr(selection, "getCount"):
        found: list[tuple[Any, Element]] = []
        for index in range(selection.getCount()):
            found.extend(_elements_in(selection.getByIndex(index)))
        return found
    return []


def insert(doc: Any, page: Any, element: Element) -> Any:
    """Insert ``element`` centred on ``page``; returns its group shape. One undo step."""
    size = elements.DEFAULT_SIZE
    x, y = (page.Width - size) // 2, (page.Height - size) // 2
    with undo.recording_locked(doc):
        group = render.render_group(
            doc,
            page,
            elements.layout_element(element, size, size),
            x,
            y,
            size,
            size,
            render.Look(scheme.load(doc)),
        )
        group.Name = elements.name(element)
    undo.add_action(
        doc,
        "Insert LibreCharts element",
        undo=lambda: page.remove(group),
        redo=lambda: page.add(group),
    )
    return group


def change(doc: Any, changes: dict[Any, Element]) -> None:
    """Give the element groups new states, as one undo step. Position and size stay."""
    previous = {group: element_of(group) for group in changes}
    look = render.Look(scheme.load(doc))

    def apply(states: dict[Any, Element | None]) -> None:
        with undo.recording_locked(doc):
            for group, element in states.items():
                if element is None:
                    continue
                size = group.Size
                render.rerender(
                    doc, group, elements.layout_element(element, size.Width, size.Height), look
                )
                group.Name = elements.name(element)

    wanted: dict[Any, Element | None] = dict(changes)
    apply(wanted)
    undo.add_action(
        doc,
        "Change LibreCharts element",
        undo=lambda: apply(previous),
        redo=lambda: apply(wanted),
    )


def fit_to_size(group: Any) -> bool:
    """Re-lay out the element in ``group`` for the group's current size; ``True`` if anything
    moved. Used after a resize: LibreOffice scales the circle to an ellipse, this puts it back."""
    element = element_of(group)
    if element is None:
        return False
    size = group.Size
    primitives = elements.layout_element(element, size.Width, size.Height)
    return render.sync_geometry(group, primitives) == "updated"
