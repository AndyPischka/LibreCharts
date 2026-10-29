# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The sidebar deck is registered and its panel follows the selection.

The panel is created like the sidebar does it, but without one (headless LibreOffice has none);
what it looks like and the clicks are checked by hand. Its contents are tested in
tests/core/test_panel.py.
"""

import datetime
import time

from helpers import close_datasheets, datasheets, dispatch, first_page, new_impress, prop

from librecharts.core.gantt import serial
from librecharts.core.messages import text
from librecharts.lo import store, ui

PANEL_URL = "private:resource/toolpanel/org.librecharts/Panel"


def _configuration(ctx, path):
    provider = ctx.getValueByName("/singletons/com.sun.star.configuration.theDefaultProvider")
    return provider.createInstanceWithArguments(
        "com.sun.star.configuration.ConfigurationAccess", (prop("nodepath", path),)
    )


def _panel(ctx, doc):
    frame = doc.getCurrentController().getFrame()
    manager = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.ui.UIElementFactoryManager", ctx
    )
    args = (prop("Frame", frame), prop("ParentWindow", frame.getContainerWindow()))
    return manager.createUIElement(PANEL_URL, args)


def _controls(element):
    """Label (the tooltip for icon-only buttons) and enabled state of every control in the panel,
    top to bottom."""
    found = []
    for control in element.getRealInterface().getControls():
        model = control.getModel()
        if not hasattr(model, "Label"):  # the scrollbar
            continue
        found.append((model.Label or model.HelpText, model.Enabled))
    return found


def test_deck_and_panel_are_registered(ctx):
    content = _configuration(ctx, "/org.openoffice.Office.UI.Sidebar/Content")
    deck = content.getByName("DeckList").getByName("org.librecharts.deck")
    assert deck.Title == "LibreCharts"
    assert deck.IconURL.endswith("/images/difference_26.png")
    panel = content.getByName("PanelList").getByName("org.librecharts.panel")
    assert panel.DeckId == "org.librecharts.deck"
    assert panel.ImplementationURL == PANEL_URL


def test_panel_follows_the_selected_chart(ctx):
    doc = new_impress(ctx)
    try:
        say = lambda key: text(key, ui.ui_locale(ctx))  # noqa: E731 - the profile's language varies
        element = _panel(ctx, doc)
        assert element is not None, "factory not found for the panel URL"
        labels = dict(_controls(element))
        assert labels[say("status_none")]
        assert labels[say("menu_edit_data")] is False
        assert labels[say("menu_add_break")] is False
        assert labels[say("menu_link_data")] is False
        assert labels[say("menu_update_all_links")] is True

        dispatch(ctx, doc, "org.librecharts:InsertColumnChart")  # selects the new chart
        labels = dict(_controls(element))
        assert any(label.startswith(say("kind_column") + ", ") for label in labels)
        assert labels[say("menu_edit_data")] is True
        assert labels[say("menu_add_break")] is True
        assert labels[say("menu_link_data")] is True
        assert labels[say("menu_remove_all")] is False

        group, _ = store.find_charts(first_page(doc))[0]
        dispatch(ctx, doc, "org.librecharts:AddAnnotation?kind=difference&start=0&end=1")
        group, _ = store.find_charts(first_page(doc))[0]
        doc.getCurrentController().select(group)
        labels = dict(_controls(element))
        assert labels[say("menu_remove_all")] is True
        difference = text("menu_bracket", ui.ui_locale(ctx), start="", end="").split(" ")[0]
        assert any(label.startswith(difference) for label in labels)
    finally:
        doc.close(True)


def test_a_redraw_refreshes_the_panel_once_not_per_shape(ctx):
    doc = new_impress(ctx)
    try:
        say = lambda key: text(key, ui.ui_locale(ctx))  # noqa: E731 - the profile's language varies
        element = _panel(ctx, doc)
        dispatch(ctx, doc, "org.librecharts:InsertGanttChart")  # selects the new chart
        dispatch(ctx, doc, "org.librecharts:EditData")
        (calc,) = datasheets(ctx)
        sheet = calc.getSheets().getByIndex(0)

        start = time.monotonic()
        sheet.getCellRangeByName("C3").setValue(serial(datetime.date(2026, 2, 10)))
        # Refreshing on every modify event of the redraw took over 20 s here, the redraw < 1 s.
        assert time.monotonic() - start < 5

        # The panel still follows a change of the document that keeps the selection.
        sheet.getCellRangeByName("A11:C11").setDataArray(
            (("Extra", serial(datetime.date(2026, 7, 1)), serial(datetime.date(2026, 7, 3))),)
        )

        def status():
            labels = [label for label, _ in _controls(element)]
            prefix = say("kind_gantt") + ", "  # not the insert button, whose tooltip is the kind
            return next((label for label in labels if label.startswith(prefix)), labels)

        deadline = time.monotonic() + 10
        while "10" not in status() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert "10" in status(), status()
    finally:
        close_datasheets(ctx)
        doc.close(True)
