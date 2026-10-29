# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""The sidebar deck is registered and its panel follows the selection.

The panel is created like the sidebar does it, but without one (headless LibreOffice has none);
what it looks like and the clicks are checked by hand. Its contents are tested in
tests/core/test_panel.py.
"""

from helpers import dispatch, first_page, new_impress, prop

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

        dispatch(ctx, doc, "org.librecharts:InsertColumnChart")  # selects the new chart
        labels = dict(_controls(element))
        assert any(label.startswith(say("kind_column") + ", ") for label in labels)
        assert labels[say("menu_edit_data")] is True
        assert labels[say("menu_add_break")] is True
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
