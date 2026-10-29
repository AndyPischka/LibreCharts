# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Colour schemes and series colours in a real LibreOffice (ADR 0016)."""

from helpers import dispatch, first_page, new_impress, prop, uno_command

from librecharts.core import style
from librecharts.lo import scheme, store

INSERT = "org.librecharts:InsertColumnChart"


def _solid_fills(group):
    """Fill colours of the solid shapes of a chart (bars and markers, not the frame or text)."""
    fills = []
    for i in range(group.getCount()):
        child = group.getByIndex(i)
        if child.FillStyle.value == "SOLID":
            fills.append(child.FillColor)
    return fills


def _state(doc, chart_id):
    state = store.read_state(doc, chart_id)
    assert state is not None
    return state


def test_a_built_in_scheme_recolours_a_chart_and_undoes_as_one_step(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        assert style.PALETTE[0] in _solid_fills(group)
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, "org.librecharts:SetScheme?name=Grey")

        assert scheme.load(doc) == style.GREY
        assert style.GREY.palette[0] in _solid_fills(group)
        assert style.PALETTE[0] not in _solid_fills(group)
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")

        assert scheme.load(doc) == style.DEFAULT
        assert style.PALETTE[0] in _solid_fills(group)
    finally:
        doc.close(True)


def test_the_scheme_reaches_text_and_line_colours(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, _ = store.find_charts(first_page(doc))[0]
        custom = style.Scheme(
            "Corporate",
            (0xEEEEEE,),
            text=0x00AA00,
            line=0x0000AA,
            font_name="Arial",
            font_size=11.0,
        )
        store.write_property(doc, store.SCHEME_PROPERTY, style.scheme_to_json(custom))
        dispatch(ctx, doc, "org.librecharts:ChangeFormat?axis=true")

        fonts = []
        colours = []
        lines = []
        for i in range(group.getCount()):
            child = group.getByIndex(i)
            if child.String:
                fonts.append(child.CharFontName)
                colours.append(child.CharColor)
            if child.LineStyle.value == "SOLID":
                lines.append(child.LineColor)
        assert fonts
        assert all(name == "Arial" for name in fonts)
        assert custom.text in colours
        assert custom.line in lines
    finally:
        doc.close(True)


def test_a_series_colour_overrides_one_palette_entry_and_undoes(ctx):
    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        group, chart_id = store.find_charts(first_page(doc))[0]
        manager = doc.getUndoManager()
        depth = len(manager.getAllUndoActionTitles())

        dispatch(ctx, doc, "org.librecharts:ChangeChart?color=0&palette=3")

        assert _state(doc, chart_id).colors == (3,)
        assert style.PALETTE[3] in _solid_fills(group)
        assert style.PALETTE[0] not in _solid_fills(group)
        assert len(manager.getAllUndoActionTitles()) == depth + 1

        uno_command(ctx, doc, ".uno:Undo")

        assert _state(doc, chart_id).colors == ()
        assert style.PALETTE[0] in _solid_fills(group)
    finally:
        doc.close(True)


def test_the_configured_default_scheme_is_readable(ctx):
    provider = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.configuration.ConfigurationProvider", ctx
    )
    access = provider.createInstanceWithArguments(
        "com.sun.star.configuration.ConfigurationAccess",
        (prop("nodepath", "/org.librecharts.Settings"),),
    )
    assert str(access.DefaultScheme) == "Default"


def test_a_scheme_survives_saving_as_odp_and_pptx(ctx):
    from helpers import save_and_reload

    doc = new_impress(ctx)
    try:
        dispatch(ctx, doc, INSERT)
        dispatch(ctx, doc, "org.librecharts:SetScheme?name=Grey")
        for fmt in ("odp", "pptx"):
            reloaded = save_and_reload(ctx, doc, fmt)
            try:
                assert scheme.load(reloaded) == style.GREY
                group, _ = store.find_charts(first_page(reloaded))[0]
                assert group.getCount() > 0
                if fmt == "odp":  # PPTX import turns shapes into custom shapes without FillColor
                    assert style.GREY.palette[0] in _solid_fills(group)
            finally:
                reloaded.close(True)
    finally:
        doc.close(True)
