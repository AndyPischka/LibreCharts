"""Public API for scripts and macros: build a deck, update links, insert a chart (M18, ADR 0028),
check a deck against a corporate design (M19, ADR 0029) and export chart data (M20, ADR 0030).

The same functions serve a Python script inside LibreOffice and the UNO service
``org.librecharts.Automation`` (``lo/automation.py``), which Basic macros call. Everything that
talks to LibreOffice is in ``lo/``; this module only names the surface and keeps it stable.

A deck specification is one JSON file, see ``core/deck.py`` and the ADR. ``DeckError`` carries a
message key, so a caller can show the reason in its own language.
"""

from __future__ import annotations

from typing import Any

from librecharts.core import deck as core_deck
from librecharts.core import designcheck as core_design
from librecharts.core import links as core_links
from librecharts.core.deck import DeckError
from librecharts.lo import chart, datasheet, deck, designcheck, links, store, templates


def build_deck(
    ctx: Any,
    template_url: str,
    spec_url: str,
    out_url: str,
    locale: str = "",
) -> str:
    """Build ``template_url`` into ``out_url`` from the deck specification at ``spec_url``.

    Every placeholder of the template that the specification names is replaced by its chart; the
    rest of the template stays as it is. ``template_url``, ``spec_url`` and ``out_url`` may be
    file URLs or system paths. ``locale`` (``de-DE``) sets the decimal separator and the language of
    magnitude suffixes of the charts, like the menu does.

    Returns what to tell the user: how many charts were written and which placeholders stayed
    empty. Raises ``DeckError`` if nothing was built; then no file was written.
    """
    spec = core_deck.parse(deck.read_spec(spec_url), locale, templates.loader(ctx, spec_url))
    return deck.build(ctx, template_url, spec, out_url, locale)


def update_links(ctx: Any, doc: Any, ids: set[str] | None = None, locale: str = "") -> str:
    """Read the sources of the linked charts of ``doc`` again and redraw what changed.

    ``ids`` limits the update to these chart ids; ``None`` updates every linked chart. All changes
    are one undo step; a chart whose data did not change only gets its new update time.

    Returns what to tell the user, ``""`` if there is nothing to say (see ``core/links.report``).
    """
    targets = links.targets(doc, ids)
    outcome = links.update(ctx, doc, targets)
    chart.apply_changes(doc, dict(outcome.changed.values()))
    # Same data: only the link's times are new. Not worth an undo step; nothing is redrawn.
    for chart_id, state in outcome.unchanged.items():
        store.write_state(doc, chart_id, state)
    for chart_id in (*outcome.changed, *outcome.unchanged):
        datasheet.refresh(doc, chart_id)
    count = len(outcome.changed) + len(outcome.unchanged)
    return core_links.report(
        count,
        len(outcome.changed),
        outcome.problems,
        locale,
        single=ids is not None and len(ids) == 1,
    )


def insert_chart(ctx: Any, doc: Any, page_index: int, spec_json: str, locale: str = "") -> str:
    """Insert one chart of the specification on slide ``page_index`` (0-based); one undo step.

    ``spec_json`` is one chart object of the deck specification; its ``placeholder`` is ignored
    here. The chart is centred on the slide, like a chart inserted from the menu.

    Returns the chart id. Raises ``DeckError`` for a bad specification or a slide that does not
    exist.
    """
    spec = core_deck.parse_chart(spec_json, locale, templates.loader(ctx))
    if doc is None:
        raise DeckError("deck_no_document")
    pages = doc.getDrawPages()
    if not isinstance(page_index, int) or not 0 <= page_index < pages.getCount():
        raise DeckError("deck_bad_slide", str(page_index))
    return store.chart_id_of(chart.insert_at(doc, pages.getByIndex(page_index), spec.state)) or ""


def check_design(doc: Any, rules_location: str, *, fix: bool = False) -> core_design.Result:
    """Check ``doc`` against the corporate design file at ``rules_location`` (URL or path).

    With ``fix`` every deviation is corrected as one undo step. The result lists what was found
    (before the fix); ``core.designcheck.report`` turns it into text. Raises ``DesignError`` for a
    file that cannot be read.
    """
    rules = designcheck.read_rules(rules_location)
    if fix:
        return designcheck.check_and_fix(doc, rules)
    return designcheck.inspect(doc, rules)
