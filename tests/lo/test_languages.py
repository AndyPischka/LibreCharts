# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""Further UI languages in a real LibreOffice (M21, ADR 0031)."""

from helpers import prop

from librecharts.core.messages import text

MENU = "/org.openoffice.Office.Addons/AddonUI/OfficeMenuBar/org.librecharts.menu/Submenu"


def _title(ctx, node, locale):
    provider = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.configuration.ConfigurationProvider", ctx
    )
    access = provider.createInstanceWithArguments(
        "com.sun.star.configuration.ConfigurationAccess",
        (prop("nodepath", f"{MENU}/{node}"), prop("Locale", locale)),
    )
    return access.Title


def test_the_installed_menu_speaks_every_shipped_language(ctx):
    for locale in ("fr", "es", "it"):
        assert _title(ctx, "m1", locale) == text("addon_insert_column", locale), locale
        assert _title(ctx, "x1", locale) == text("menu_export_csv", locale), locale


def test_a_language_without_translation_shows_english(ctx):
    assert _title(ctx, "m1", "pt-BR") == text("addon_insert_column", "en")
