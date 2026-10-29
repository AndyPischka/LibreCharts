"""User-visible strings. Every message must exist in English and German (AGENTS.md)."""

from __future__ import annotations

FALLBACK_LANGUAGE = "en"

MESSAGES: dict[str, dict[str, str]] = {
    "datasheet_title": {
        "en": "LibreCharts data",
        "de": "LibreCharts-Daten",
    },
    "select_chart": {
        "en": "Please select a LibreCharts chart first.",
        "de": "Bitte zuerst ein LibreCharts-Diagramm auswählen.",
    },
    "orphaned_chart": {
        "en": (
            "The data of this chart is not stored in this presentation, probably because the "
            "chart was copied from another one. It still displays correctly but cannot be edited."
        ),
        "de": (
            "Die Daten dieses Diagramms sind nicht in dieser Präsentation gespeichert, vermutlich "
            "wurde es aus einer anderen kopiert. Es wird weiterhin korrekt angezeigt, kann aber "
            "nicht bearbeitet werden."
        ),
    },
    "annotation_unsupported": {
        "en": "This annotation is not available for this chart type yet.",
        "de": "Diese Annotation gibt es für diesen Diagrammtyp noch nicht.",
    },
    "pick_start": {
        "en": "Click the column the arrow starts at. Esc cancels.",
        "de": "Säule anklicken, an der der Pfeil beginnt. Esc bricht ab.",
    },
    "pick_end": {
        "en": "Now click the column the arrow points to. Esc cancels.",
        "de": "Jetzt die Säule anklicken, auf die der Pfeil zeigt. Esc bricht ab.",
    },
    "menu_edit_data": {
        "en": "Edit chart data",
        "de": "Diagrammdaten bearbeiten",
    },
    "menu_add_difference": {
        "en": "Add difference arrow",
        "de": "Differenzpfeil hinzufügen",
    },
    "menu_add_level": {
        "en": "Add level difference",
        "de": "Niveaudifferenz hinzufügen",
    },
    "menu_add_cagr": {
        "en": "Add CAGR arrow",
        "de": "CAGR-Pfeil hinzufügen",
    },
    "menu_bracket": {
        "en": "Difference {start} → {end}",
        "de": "Differenz {start} → {end}",
    },
    "menu_level": {
        "en": "Level difference {start} → {end}",
        "de": "Niveaudifferenz {start} → {end}",
    },
    "menu_cagr": {
        "en": "CAGR {start} → {end}",
        "de": "CAGR {start} → {end}",
    },
    "menu_add_break": {
        "en": "Add axis break",
        "de": "Achsenbruch hinzufügen",
    },
    "menu_axis_break": {
        "en": "Axis break ({range})",
        "de": "Achsenbruch ({range})",
    },
    "menu_change_break": {
        "en": "Change axis break...",
        "de": "Achsenbruch ändern...",
    },
    "break_title": {
        "en": "Axis break",
        "de": "Achsenbruch",
    },
    "break_auto": {
        "en": "Automatic",
        "de": "Automatisch",
    },
    "break_manual": {
        "en": "Remove the values between",
        "de": "Werte entfernen zwischen",
    },
    "break_lower": {
        "en": "Lower value:",
        "de": "Unterer Wert:",
    },
    "break_upper": {
        "en": "Upper value:",
        "de": "Oberer Wert:",
    },
    "break_hint": {
        "en": "The tallest column reaches {tallest}.",
        "de": "Die höchste Säule reicht bis {tallest}.",
    },
    "break_not_a_number": {
        "en": "Please enter numbers.",
        "de": "Bitte Zahlen eingeben.",
    },
    "break_order": {
        "en": "The lower value must be at least 0 and below the upper value.",
        "de": "Der untere Wert muss mindestens 0 und kleiner als der obere sein.",
    },
    "break_hint_waterfall": {
        "en": "The break must lie below all steps, up to {tallest}.",
        "de": "Der Bruch muss unterhalb aller Schritte liegen, bis {tallest}.",
    },
    "break_too_high_waterfall": {
        "en": "The upper value must not exceed the lowest step.",
        "de": "Der obere Wert darf den niedrigsten Schritt nicht übersteigen.",
    },
    "break_too_high": {
        "en": "The upper value must not exceed the tallest column.",
        "de": "Der obere Wert darf die höchste Säule nicht übersteigen.",
    },
    "button_ok": {
        "en": "OK",
        "de": "OK",
    },
    "button_cancel": {
        "en": "Cancel",
        "de": "Abbrechen",
    },
    "menu_show_absolute": {
        "en": "Show absolute difference",
        "de": "Absolute Differenz zeigen",
    },
    "menu_show_percent": {
        "en": "Show percentage",
        "de": "Prozent zeigen",
    },
    "menu_as_level": {
        "en": "Show as level difference",
        "de": "Als Niveaudifferenz zeigen",
    },
    "menu_as_bracket": {
        "en": "Show as arrow above the columns",
        "de": "Als Pfeil über den Säulen zeigen",
    },
    "menu_remove": {
        "en": "Remove",
        "de": "Entfernen",
    },
    "menu_remove_all": {
        "en": "Remove all annotations",
        "de": "Alle Annotationen entfernen",
    },
    "menu_mekko_units": {
        "en": "Show with units",
        "de": "Mit Einheiten anzeigen",
    },
    "menu_mekko_percent": {
        "en": "Show as 100 %",
        "de": "Als 100 % anzeigen",
    },
    "option_unsupported": {
        "en": "This option is not available for this chart type.",
        "de": "Diese Option gibt es für diesen Diagrammtyp nicht.",
    },
    "corrupt_chart": {
        "en": "The data of this chart cannot be read: {detail}",
        "de": "Die Daten dieses Diagramms können nicht gelesen werden: {detail}",
    },
    "sidebar_title": {
        "en": "LibreCharts",
        "de": "LibreCharts",
    },
    "panel_insert": {
        "en": "Insert chart",
        "de": "Diagramm einfügen",
    },
    "panel_chart": {
        "en": "Selected chart",
        "de": "Ausgewähltes Diagramm",
    },
    "panel_annotations": {
        "en": "Add annotation",
        "de": "Annotation hinzufügen",
    },
    "panel_list": {
        "en": "Annotations on this chart",
        "de": "Annotationen dieses Diagramms",
    },
    "panel_no_annotations": {
        "en": "None yet.",
        "de": "Noch keine.",
    },
    "insert_column": {
        "en": "Column chart",
        "de": "Säulendiagramm",
    },
    "insert_bar": {
        "en": "Bar chart",
        "de": "Balkendiagramm",
    },
    "insert_waterfall": {
        "en": "Waterfall chart",
        "de": "Wasserfalldiagramm",
    },
    "insert_mekko": {
        "en": "Marimekko chart",
        "de": "Marimekko-Diagramm",
    },
    "kind_column": {
        "en": "Column chart",
        "de": "Säulendiagramm",
    },
    "kind_bar": {
        "en": "Bar chart",
        "de": "Balkendiagramm",
    },
    "kind_waterfall": {
        "en": "Waterfall chart",
        "de": "Wasserfalldiagramm",
    },
    "kind_mekko": {
        "en": "Marimekko chart",
        "de": "Marimekko-Diagramm",
    },
    "kind_mekko_units": {
        "en": "Marimekko chart (units)",
        "de": "Marimekko-Diagramm (Einheiten)",
    },
    "status_none": {
        "en": "No chart selected.",
        "de": "Kein Diagramm ausgewählt.",
    },
    "status_chart": {
        "en": "{kind}, {count} categories",
        "de": "{kind}, {count} Kategorien",
    },
    "status_orphaned": {
        "en": "This chart's data is not in this presentation.",
        "de": "Die Daten dieses Diagramms sind nicht in dieser Präsentation.",
    },
}


def text(key: str, locale: str, **fields: str) -> str:
    """The message ``key`` for a LibreOffice locale like ``de-DE``; English if unsupported."""
    language = locale.split("-")[0].lower()
    table = MESSAGES[key]
    return table.get(language, table[FALLBACK_LANGUAGE]).format(**fields)
