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
    "menu_stacked": {
        "en": "Show stacked",
        "de": "Gestapelt anzeigen",
    },
    "menu_clustered": {
        "en": "Show clustered",
        "de": "Gruppiert anzeigen",
    },
    "menu_percent": {
        "en": "Show as 100 %",
        "de": "Als 100 % anzeigen",
    },
    "menu_sort": {
        "en": "Sort categories",
        "de": "Kategorien sortieren",
    },
    "menu_sort_none": {
        "en": "Data sheet order",
        "de": "Reihenfolge der Daten",
    },
    "menu_sort_descending": {
        "en": "Descending",
        "de": "Absteigend",
    },
    "menu_sort_ascending": {
        "en": "Ascending",
        "de": "Aufsteigend",
    },
    "menu_format": {
        "en": "Format",
        "de": "Format",
    },
    "menu_axis": {
        "en": "Value axis",
        "de": "Wertachse",
    },
    "menu_axis_show": {
        "en": "Show value axis",
        "de": "Wertachse anzeigen",
    },
    "menu_axis_hide": {
        "en": "Hide value axis",
        "de": "Wertachse ausblenden",
    },
    "menu_gridlines": {
        "en": "Gridlines",
        "de": "Gitternetzlinien",
    },
    "menu_gridlines_show": {
        "en": "Show gridlines",
        "de": "Gitternetzlinien anzeigen",
    },
    "menu_gridlines_hide": {
        "en": "Hide gridlines",
        "de": "Gitternetzlinien ausblenden",
    },
    "menu_series_names": {
        "en": "Series names",
        "de": "Reihennamen",
    },
    "menu_series_none": {
        "en": "Hide series names",
        "de": "Reihennamen ausblenden",
    },
    "menu_series_labels": {
        "en": "Show series labels",
        "de": "Reihennamen anzeigen",
    },
    "menu_series_legend": {
        "en": "Show legend",
        "de": "Legende anzeigen",
    },
    "menu_markers_show": {
        "en": "Show point markers",
        "de": "Punktmarkierungen anzeigen",
    },
    "menu_markers_hide": {
        "en": "Hide point markers",
        "de": "Punktmarkierungen ausblenden",
    },
    "menu_line_series": {
        "en": "Series as lines",
        "de": "Reihen als Linien",
    },
    "menu_series_as_line": {
        "en": "{name} as line",
        "de": "{name} als Linie",
    },
    "menu_series_as_column": {
        "en": "{name} as column",
        "de": "{name} als S\u00e4ule",
    },
    "menu_secondary_axis": {
        "en": "{name} on secondary axis",
        "de": "{name} auf zweiter Achse",
    },
    "menu_primary_axis": {
        "en": "{name} on primary axis",
        "de": "{name} auf erster Achse",
    },
    "menu_number_format": {
        "en": "Number format...",
        "de": "Zahlenformat...",
    },
    "menu_add_value_line": {
        "en": "Add value line...",
        "de": "Wertlinie hinzufügen...",
    },
    "menu_value_line": {
        "en": "Value line ({value})",
        "de": "Wertlinie ({value})",
    },
    "menu_value_line_average": {
        "en": "average",
        "de": "Durchschnitt",
    },
    "menu_change_value_line": {
        "en": "Change value line...",
        "de": "Wertlinie ändern...",
    },
    "panel_format": {
        "en": "Format",
        "de": "Format",
    },
    "format_title": {
        "en": "Number format",
        "de": "Zahlenformat",
    },
    "format_decimals": {
        "en": "Decimals (empty: automatic):",
        "de": "Nachkommastellen (leer: automatisch):",
    },
    "format_magnitude": {
        "en": "Magnitude:",
        "de": "Größenordnung:",
    },
    "format_unit": {
        "en": "Unit:",
        "de": "Einheit:",
    },
    "format_separator": {
        "en": "Decimal separator:",
        "de": "Dezimaltrennzeichen:",
    },
    "format_separator_dot": {
        "en": "Point (1.5)",
        "de": "Punkt (1.5)",
    },
    "format_separator_comma": {
        "en": "Comma (1,5)",
        "de": "Komma (1,5)",
    },
    "format_decimals_invalid": {
        "en": "Enter a whole number from 0 to 4, or leave the field empty.",
        "de": "Bitte eine ganze Zahl von 0 bis 4 eingeben oder das Feld leer lassen.",
    },
    "format_unit_too_long": {
        "en": "The unit must be at most 10 characters long.",
        "de": "Die Einheit darf höchstens 10 Zeichen lang sein.",
    },
    "format_magnitude_invalid": {
        "en": "Choose a magnitude.",
        "de": "Bitte eine Größenordnung wählen.",
    },
    "format_separator_invalid": {
        "en": "Choose a decimal separator.",
        "de": "Bitte ein Dezimaltrennzeichen wählen.",
    },
    "format_magnitude_none": {
        "en": "None",
        "de": "Keine",
    },
    "format_magnitude_thousands": {
        "en": "Thousands (k)",
        "de": "Tausender (Tsd.)",
    },
    "format_magnitude_millions": {
        "en": "Millions (M)",
        "de": "Millionen (Mio.)",
    },
    "format_magnitude_billions": {
        "en": "Billions (bn)",
        "de": "Milliarden (Mrd.)",
    },
    "value_line_title": {
        "en": "Value line",
        "de": "Wertlinie",
    },
    "value_line_average": {
        "en": "Average",
        "de": "Durchschnitt",
    },
    "value_line_value": {
        "en": "Value:",
        "de": "Wert:",
    },
    "value_line_not_a_number": {
        "en": "Please enter a number.",
        "de": "Bitte eine Zahl eingeben.",
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
    "insert_line": {
        "en": "Line chart",
        "de": "Liniendiagramm",
    },
    "insert_area": {
        "en": "Area chart",
        "de": "Fl\u00e4chendiagramm",
    },
    "insert_pie": {
        "en": "Pie chart",
        "de": "Kreisdiagramm",
    },
    "insert_scatter": {
        "en": "Scatter chart",
        "de": "Streudiagramm",
    },
    "insert_butterfly": {
        "en": "Butterfly chart",
        "de": "Schmetterlingsdiagramm",
    },
    "insert_gantt": {
        "en": "Gantt chart",
        "de": "Gantt-Diagramm",
    },
    "kind_gantt": {
        "en": "Gantt chart",
        "de": "Gantt-Diagramm",
    },
    "status_gantt": {
        "en": "{kind}, {count} rows",
        "de": "{kind}, {count} Zeilen",
    },
    "menu_sort_start": {
        "en": "By start date",
        "de": "Nach Startdatum",
    },
    "menu_add_date_line": {
        "en": "Add date line...",
        "de": "Datumslinie hinzufügen...",
    },
    "menu_add_today_line": {
        "en": "Add today line",
        "de": "Heute-Linie hinzufügen",
    },
    "menu_date_line": {
        "en": "Date line ({value})",
        "de": "Datumslinie ({value})",
    },
    "menu_change_date_line": {
        "en": "Change date line...",
        "de": "Datumslinie ändern...",
    },
    "menu_gantt_bars": {
        "en": "Bars",
        "de": "Balken",
    },
    "date_line_title": {
        "en": "Date line",
        "de": "Datumslinie",
    },
    "date_line_date": {
        "en": "Date (e.g. 2026-06-30):",
        "de": "Datum (z. B. 30.06.2026):",
    },
    "date_line_invalid": {
        "en": "Please enter a date such as 2026-06-30 or 6/30/2026.",
        "de": "Bitte ein Datum wie 30.06.2026 eingeben.",
    },
    "gantt_months": {
        "en": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
        "de": "Jan,Feb,Mär,Apr,Mai,Jun,Jul,Aug,Sep,Okt,Nov,Dez",
    },
    "gantt_quarter": {
        "en": "Q{number}",
        "de": "Q{number}",
    },
    "gantt_decade": {
        "en": "{year}s",
        "de": "{year}er",
    },
    "kind_pie": {
        "en": "Pie chart",
        "de": "Kreisdiagramm",
    },
    "kind_doughnut": {
        "en": "Doughnut chart",
        "de": "Ringdiagramm",
    },
    "kind_scatter": {
        "en": "Scatter chart",
        "de": "Streudiagramm",
    },
    "kind_bubble": {
        "en": "Bubble chart",
        "de": "Blasendiagramm",
    },
    "kind_butterfly": {
        "en": "Butterfly chart",
        "de": "Schmetterlingsdiagramm",
    },
    "status_butterfly_extra": {
        "en": "Only the first two series are drawn.",
        "de": "Nur die ersten beiden Reihen werden gezeichnet.",
    },
    "menu_pie": {
        "en": "Pie chart",
        "de": "Kreisdiagramm",
    },
    "menu_doughnut": {
        "en": "Doughnut chart",
        "de": "Ringdiagramm",
    },
    "kind_column": {
        "en": "Column chart",
        "de": "Säulendiagramm",
    },
    "kind_column_percent": {
        "en": "Column chart (100 %)",
        "de": "Säulendiagramm (100 %)",
    },
    "kind_bar": {
        "en": "Bar chart",
        "de": "Balkendiagramm",
    },
    "kind_bar_percent": {
        "en": "Bar chart (100 %)",
        "de": "Balkendiagramm (100 %)",
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
    "kind_line": {
        "en": "Line chart",
        "de": "Liniendiagramm",
    },
    "kind_area": {
        "en": "Area chart",
        "de": "Fl\u00e4chendiagramm",
    },
    "kind_area_percent": {
        "en": "Area chart (100 %)",
        "de": "Fl\u00e4chendiagramm (100 %)",
    },
    "kind_column_lines": {
        "en": "Column chart with lines",
        "de": "S\u00e4ulendiagramm mit Linien",
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
    "menu_same_scale": {
        "en": "Same scale",
        "de": "Gleicher Maßstab",
    },
    "menu_remove_same_scale": {
        "en": "Own scale",
        "de": "Eigener Maßstab",
    },
    "menu_series_color": {
        "en": "Series colour",
        "de": "Reihenfarbe",
    },
    "menu_color_default": {
        "en": "Default colour",
        "de": "Standardfarbe",
    },
    "menu_color": {
        "en": "Colour {index}",
        "de": "Farbe {index}",
    },
    "menu_copy_format": {
        "en": "Copy chart format",
        "de": "Diagrammformat kopieren",
    },
    "menu_apply_format": {
        "en": "Apply chart format",
        "de": "Diagrammformat übernehmen",
    },
    "menu_scheme": {
        "en": "Colour scheme",
        "de": "Farbschema",
    },
    "same_scale_need_two": {
        "en": "Select at least two LibreCharts charts for a shared scale.",
        "de": (
            "Bitte mindestens zwei LibreCharts-Diagramme für einen gemeinsamen Maßstab auswählen."
        ),
    },
    "same_scale_incompatible": {
        "en": (
            "These charts cannot share a scale: percent charts and charts with a different "
            "orientation (columns and bars) cannot be combined."
        ),
        "de": (
            "Diese Diagramme können keinen Maßstab teilen: Prozentdiagramme und Diagramme mit "
            "anderer Ausrichtung (Säulen und Balken) lassen sich nicht kombinieren."
        ),
    },
    "format_copied": {
        "en": "Chart format copied. Select other charts and apply it.",
        "de": "Diagrammformat kopiert. Andere Diagramme auswählen und übernehmen.",
    },
    "format_not_copied": {
        "en": "Copy a chart format first.",
        "de": "Bitte zuerst ein Diagrammformat kopieren.",
    },
    "panel_document": {
        "en": "Document",
        "de": "Dokument",
    },
    "panel_scheme": {
        "en": "Colour scheme",
        "de": "Farbschema",
    },
    "panel_scheme_load": {
        "en": "Load scheme...",
        "de": "Schema laden...",
    },
    "panel_scheme_save": {
        "en": "Save scheme...",
        "de": "Schema speichern...",
    },
    "scheme_title_load": {
        "en": "Load colour scheme",
        "de": "Farbschema laden",
    },
    "scheme_title_save": {
        "en": "Save colour scheme",
        "de": "Farbschema speichern",
    },
    "scheme_filter": {
        "en": "LibreCharts colour scheme (*.json)",
        "de": "LibreCharts-Farbschema (*.json)",
    },
    "scheme_unknown": {
        "en": "Unknown colour scheme.",
        "de": "Unbekanntes Farbschema.",
    },
    "scheme_load_failed": {
        "en": "The colour scheme could not be loaded: {detail}",
        "de": "Das Farbschema konnte nicht geladen werden: {detail}",
    },
    "scheme_save_failed": {
        "en": "The colour scheme could not be saved: {detail}",
        "de": "Das Farbschema konnte nicht gespeichert werden: {detail}",
    },
    "scheme_loaded": {
        "en": "Colour scheme '{name}' loaded.",
        "de": "Farbschema '{name}' geladen.",
    },
    "scheme_saved": {
        "en": "Colour scheme saved to {path}.",
        "de": "Farbschema gespeichert unter {path}.",
    },
}


def text(key: str, locale: str, **fields: str) -> str:
    """The message ``key`` for a LibreOffice locale like ``de-DE``; English if unsupported."""
    language = locale.split("-")[0].lower()
    table = MESSAGES[key]
    return table.get(language, table[FALLBACK_LANGUAGE]).format(**fields)
