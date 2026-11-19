"""User-visible strings: English and German here, further languages in ``locales/`` (ADR 0031).

Every message exists in English and German in ``MESSAGES`` (AGENTS.md); they are the source of the
translations. Further languages are flat JSON files ``locales/<language>.json`` (key -> text), the
format the translation platform (Weblate) edits. ``locales/en.json`` and ``locales/de.json`` are
generated from ``MESSAGES`` by ``uv run poe locales`` as the platform's source and reference. A
message missing from a language falls back to English.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import cast

FALLBACK_LANGUAGE = "en"
SOURCE_LANGUAGES = ("en", "de")  # kept in MESSAGES, never read from locales/
LOCALES = Path(__file__).resolve().parent / "locales"

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
    "pick_gap_start": {
        "en": "Click one of the two categories the gap opens between. Esc cancels.",
        "de": (
            "Eine der beiden Kategorien anklicken, zwischen denen die Lücke entstehen soll. "
            "Esc bricht ab."
        ),
    },
    "pick_gap_end": {
        "en": "Now click the second category, next to the first. Esc cancels.",
        "de": "Jetzt die zweite Kategorie anklicken, direkt neben der ersten. Esc bricht ab.",
    },
    "pick_bracket_start": {
        "en": "Click the first category of the group bracket. Esc cancels.",
        "de": "Die erste Kategorie der Gruppenklammer anklicken. Esc bricht ab.",
    },
    "pick_bracket_end": {
        "en": "Now click the last category of the group bracket. Esc cancels.",
        "de": "Jetzt die letzte Kategorie der Gruppenklammer anklicken. Esc bricht ab.",
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
    "menu_add_gap": {
        "en": "Add category gap",
        "de": "Kategorielücke hinzufügen",
    },
    "menu_add_group_bracket": {
        "en": "Add group bracket",
        "de": "Gruppenklammer hinzufügen",
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
    "menu_between": {
        "en": "Difference {start} vs. {end}",
        "de": "Differenz {start} vs. {end}",
    },
    "menu_gap": {
        "en": "Gap between {start} and {end}",
        "de": "Lücke zwischen {start} und {end}",
    },
    "menu_group_bracket": {
        "en": "Bracket over {start} to {end}",
        "de": "Klammer von {start} bis {end}",
    },
    "menu_change_text": {
        "en": "Change text...",
        "de": "Text ändern...",
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
        "de": "Werte dazwischen entfernen",
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
    "bracket_title": {
        "en": "Group bracket",
        "de": "Gruppenklammer",
    },
    "bracket_text": {
        "en": "Text:",
        "de": "Text:",
    },
    "bracket_text_missing": {
        "en": "Please enter a text for the bracket.",
        "de": "Bitte einen Text für die Klammer eingeben.",
    },
    "bracket_text_too_long": {
        "en": "The text must be at most 80 characters long.",
        "de": "Der Text darf höchstens 80 Zeichen lang sein.",
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
        "en": "Show percentage difference",
        "de": "Prozentuale Differenz zeigen",
    },
    "menu_as_level": {
        "en": "Show as level difference",
        "de": "Als Niveaudifferenz zeigen",
    },
    "menu_as_bracket": {
        "en": "Show as difference arrow",
        "de": "Als Differenzpfeil zeigen",
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
        "de": "Reihenfolge im Datenblatt",
    },
    "menu_sort_descending": {
        "en": "Descending",
        "de": "Absteigend",
    },
    "menu_sort_ascending": {
        "en": "Ascending",
        "de": "Aufsteigend",
    },
    "menu_sort_segments": {
        "en": "Sort segments",
        "de": "Segmente sortieren",
    },
    "menu_floating": {
        "en": "Floating bars",
        "de": "Schwebende Balken",
    },
    "menu_baseline": {
        "en": "Bars from the baseline",
        "de": "Balken von der Grundlinie",
    },
    "menu_error_bars": {
        "en": "Error bars",
        "de": "Fehlerbalken",
    },
    "menu_no_error_bars": {
        "en": "No error bars",
        "de": "Keine Fehlerbalken",
    },
    "menu_waterfall_vertical": {
        "en": "Vertical",
        "de": "Vertikal",
    },
    "menu_waterfall_horizontal": {
        "en": "Horizontal",
        "de": "Horizontal",
    },
    "menu_waterfall_single": {
        "en": "Single running total",
        "de": "Eine laufende Summe",
    },
    "menu_waterfall_stacked": {
        "en": "Stacked",
        "de": "Gestapelt",
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
        "en": "Series labels",
        "de": "Reihennamen",
    },
    "menu_series_none": {
        "en": "Hide series labels",
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
    "status_gantt_calendar": {
        "en": "{kind}, {count} rows, working days",
        "de": "{kind}, {count} Zeilen, Arbeitstage",
    },
    "menu_working_days": {
        "en": "Working days",
        "de": "Arbeitstage",
    },
    "menu_import": {
        "en": "Import",
        "de": "Importieren",
    },
    "menu_import_csv": {
        "en": "From CSV...",
        "de": "Aus CSV...",
    },
    "menu_import_project": {
        "en": "From ProjectLibre...",
        "de": "Aus ProjectLibre...",
    },
    "import_csv_title": {
        "en": "Import from CSV",
        "de": "Aus CSV importieren",
    },
    "import_project_title": {
        "en": "Import from ProjectLibre",
        "de": "Aus ProjectLibre importieren",
    },
    "import_data_title": {
        "en": "Import data",
        "de": "Daten importieren",
    },
    "import_data_filter": {
        "en": "Data files",
        "de": "Datendateien",
    },
    "import_data_failed": {
        "en": "The data cannot be imported: {detail}",
        "de": "Die Daten lassen sich nicht importieren: {detail}",
    },
    "clipboard_empty": {
        "en": "The clipboard holds no table.",
        "de": "Die Zwischenablage enthält keine Tabelle.",
    },
    "import_invalid": {
        "en": "The table is not valid.",
        "de": "Die Tabelle ist ungültig.",
    },
    "import_too_small": {
        "en": "The table needs a header and at least one row and column.",
        "de": "Die Tabelle braucht eine Kopfzeile und mindestens eine Zeile und Spalte.",
    },
    "import_csv_filter": {
        "en": "CSV files",
        "de": "CSV-Dateien",
    },
    "import_project_filter": {
        "en": "Project files",
        "de": "Projektdateien",
    },
    "import_failed": {
        "en": "The file could not be imported: {detail}",
        "de": "Die Datei konnte nicht importiert werden: {detail}",
    },
    "import_empty": {
        "en": "The file has no activities.",
        "de": "Die Datei enthält keine Vorgänge.",
    },
    "import_too_large": {
        "en": "The file is too large.",
        "de": "Die Datei ist zu groß.",
    },
    "import_too_many_rows": {
        "en": "The file has too many rows.",
        "de": "Die Datei hat zu viele Zeilen.",
    },
    "import_not_project": {
        "en": "The file is not a ProjectLibre or MS Project XML file.",
        "de": "Die Datei ist keine ProjectLibre- oder MS-Project-XML-Datei.",
    },
    "import_linked": {
        "en": "Remove the data link first.",
        "de": "Bitte zuerst die Datenverknüpfung entfernen.",
    },
    "import_not_gantt": {
        "en": "Only a Gantt chart can import project data.",
        "de": "Nur ein Gantt-Diagramm kann Projektdaten importieren.",
    },
    "import_done": {
        "en": "Imported {count} rows.",
        "de": "{count} Zeilen importiert.",
    },
    "menu_working_all": {
        "en": "All days",
        "de": "Alle Tage",
    },
    "menu_working_weekdays": {
        "en": "Monday to Friday",
        "de": "Montag bis Freitag",
    },
    "menu_working_custom": {
        "en": "Custom...",
        "de": "Benutzerdefiniert...",
    },
    "working_days_title": {
        "en": "Working days",
        "de": "Arbeitstage",
    },
    "working_days_names": {
        "en": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        "de": "Mo,Di,Mi,Do,Fr,Sa,So",
    },
    "working_days_holidays": {
        "en": "Holidays (one date per line):",
        "de": "Feiertage (ein Datum pro Zeile):",
    },
    "working_days_bad_date": {
        "en": "Please enter dates such as 2026-12-25 or 25.12.2026.",
        "de": "Bitte Daten wie 25.12.2026 eingeben.",
    },
    "working_days_none": {
        "en": "Choose at least one working day.",
        "de": "Bitte mindestens einen Arbeitstag wählen.",
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
    "scheme_default": {
        "en": "Default",
        "de": "Standard",
    },
    "scheme_grey": {
        "en": "Grey",
        "de": "Grau",
    },
    "scheme_high_contrast": {
        "en": "High contrast",
        "de": "Hoher Kontrast",
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
    "menu_link_data": {
        "en": "Link data...",
        "de": "Daten verknüpfen...",
    },
    "menu_data_link": {
        "en": "Data link",
        "de": "Datenverknüpfung",
    },
    "menu_update_link": {
        "en": "Update link",
        "de": "Verknüpfung aktualisieren",
    },
    "menu_change_link": {
        "en": "Change link...",
        "de": "Verknüpfung ändern...",
    },
    "menu_open_source": {
        "en": "Open source file",
        "de": "Quelldatei öffnen",
    },
    "menu_remove_link": {
        "en": "Remove link",
        "de": "Verknüpfung entfernen",
    },
    "menu_update_all_links": {
        "en": "Update all links",
        "de": "Alle Verknüpfungen aktualisieren",
    },
    "menu_show_data": {
        "en": "Show chart data",
        "de": "Diagrammdaten anzeigen",
    },
    "status_linked": {
        "en": "Linked to {source}.",
        "de": "Verknüpft mit {source}.",
    },
    "status_linked_updated": {
        "en": "Linked to {source}, updated {time}.",
        "de": "Verknüpft mit {source}, aktualisiert {time}.",
    },
    "datasheet_title_linked": {
        "en": "LibreCharts data (read-only): {source}",
        "de": "LibreCharts-Daten (schreibgeschützt): {source}",
    },
    "datasheet_linked": {
        "en": "This chart takes its data from {source}.",
        "de": "Dieses Diagramm bezieht seine Daten aus {source}.",
    },
    "datasheet_linked_hint": {
        "en": "Change the data there, then update the link.",
        "de": "Die Daten dort ändern, dann die Verknüpfung aktualisieren.",
    },
    "link_title": {
        "en": "Link data",
        "de": "Daten verknüpfen",
    },
    "link_file": {
        "en": "File:",
        "de": "Datei:",
    },
    "link_browse": {
        "en": "Browse...",
        "de": "Durchsuchen...",
    },
    "link_sheet": {
        "en": "Sheet:",
        "de": "Tabelle:",
    },
    "link_range": {
        "en": "Range or name:",
        "de": "Bereich oder Name:",
    },
    "link_hint": {
        "en": (
            "The first row and column hold the names, as in the data sheet. A named range "
            "follows the source when it grows."
        ),
        "de": (
            "Die erste Zeile und Spalte enthalten die Namen, wie im Datenblatt. Ein benannter "
            "Bereich wächst mit der Quelle mit."
        ),
    },
    "link_filter": {
        "en": "Spreadsheets (*.ods, *.xlsx, *.xls, *.csv)",
        "de": "Tabellendokumente (*.ods, *.xlsx, *.xls, *.csv)",
    },
    "link_no_file": {
        "en": "Please choose a file.",
        "de": "Bitte eine Datei auswählen.",
    },
    "link_no_range_given": {
        "en": "Please enter a range such as B2:F6 or the name of a named range.",
        "de": "Bitte einen Bereich wie B2:F6 oder den Namen eines benannten Bereichs eingeben.",
    },
    "link_no_sheet_given": {
        "en": "Please choose a sheet.",
        "de": "Bitte eine Tabelle auswählen.",
    },
    "link_bad_range": {
        "en": "'{range}' is neither a range such as B2:F6 nor the name of a named range.",
        "de": "'{range}' ist weder ein Bereich wie B2:F6 noch der Name eines benannten Bereichs.",
    },
    "link_missing": {
        "en": "The file {file} was not found.",
        "de": "Die Datei {file} wurde nicht gefunden.",
    },
    "link_open_failed": {
        "en": "The file {file} cannot be opened as a spreadsheet.",
        "de": "Die Datei {file} lässt sich nicht als Tabellendokument öffnen.",
    },
    "link_no_sheet": {
        "en": "There is no sheet '{sheet}' in {file}.",
        "de": "In {file} gibt es keine Tabelle '{sheet}'.",
    },
    "link_no_range": {
        "en": "There is no range '{range}' in {file}.",
        "de": "In {file} gibt es keinen Bereich '{range}'.",
    },
    "link_too_small": {
        "en": "The range needs at least two rows and two columns.",
        "de": "Der Bereich braucht mindestens zwei Zeilen und zwei Spalten.",
    },
    "link_too_large": {
        "en": "The range is too large: at most {cells} cells.",
        "de": "Der Bereich ist zu groß: höchstens {cells} Zellen.",
    },
    "link_unchanged": {
        "en": "The linked data has not changed.",
        "de": "Die verknüpften Daten haben sich nicht geändert.",
    },
    "link_not_linked": {
        "en": "This chart is not linked to a file.",
        "de": "Dieses Diagramm ist nicht mit einer Datei verknüpft.",
    },
    "links_none": {
        "en": "This presentation has no linked charts.",
        "de": "Diese Präsentation hat keine verknüpften Diagramme.",
    },
    "links_summary": {
        "en": "{changed} of {count} linked charts changed.",
        "de": "{changed} von {count} verknüpften Diagrammen geändert.",
    },
    "links_problems": {
        "en": "Not updated:",
        "de": "Nicht aktualisiert:",
    },
    "link_problem": {
        "en": "Slide {slide}: {reason}",
        "de": "Folie {slide}: {reason}",
    },
    "infobar_links_changed": {
        "en": "Linked data of this presentation has changed.",
        "de": "Verknüpfte Daten dieser Präsentation wurden geändert.",
    },
    "infobar_links_question": {
        "en": "Update the linked charts now?",
        "de": "Die verknüpften Diagramme jetzt aktualisieren?",
    },
    "infobar_update_now": {
        "en": "Update now",
        "de": "Jetzt aktualisieren",
    },
    "panel_agenda": {
        "en": "Agenda",
        "de": "Agenda",
    },
    "menu_insert_agenda": {
        "en": "Insert agenda",
        "de": "Agenda einfügen",
    },
    "menu_start_chapter": {
        "en": "Start chapter here",
        "de": "Kapitel hier beginnen",
    },
    "menu_update_agenda": {
        "en": "Update agenda",
        "de": "Agenda aktualisieren",
    },
    "agenda_title": {
        "en": "Agenda",
        "de": "Agenda",
    },
    "agenda_placeholder": {
        "en": "Chapter {number}",
        "de": "Kapitel {number}",
    },
    "agenda_new_chapter": {
        "en": "New chapter",
        "de": "Neues Kapitel",
    },
    "agenda_exists": {
        "en": (
            "This presentation already has an agenda. Edit its chapters on the agenda slide, one "
            "per line, then choose Update agenda."
        ),
        "de": (
            "Diese Präsentation hat schon eine Agenda. Die Kapitel auf der Agenda-Folie "
            "bearbeiten, eines pro Zeile, dann Agenda aktualisieren wählen."
        ),
    },
    "agenda_missing": {
        "en": "This presentation has no agenda yet. Insert one first.",
        "de": "Diese Präsentation hat noch keine Agenda. Bitte zuerst eine einfügen.",
    },
    "agenda_empty": {
        "en": (
            "The agenda needs at least one chapter. Write one chapter per line on the agenda slide."
        ),
        "de": (
            "Die Agenda braucht mindestens ein Kapitel. Auf der Agenda-Folie ein Kapitel pro Zeile "
            "schreiben."
        ),
    },
    "agenda_on_agenda_slide": {
        "en": "A chapter starts on a content slide. Select the first slide of the chapter.",
        "de": (
            "Ein Kapitel beginnt auf einer Inhaltsfolie. Bitte die erste Folie des Kapitels wählen."
        ),
    },
    "agenda_first_slide": {
        "en": "A chapter cannot start on the first slide.",
        "de": "Ein Kapitel kann nicht auf der ersten Folie beginnen.",
    },
    "insert_harvey": {
        "en": "Harvey ball",
        "de": "Harvey Ball",
    },
    "insert_check": {
        "en": "Check mark",
        "de": "Häkchen",
    },
    "panel_elements": {
        "en": "Elements",
        "de": "Elemente",
    },
    "panel_arrange": {
        "en": "Arrange",
        "de": "Anordnen",
    },
    "select_element": {
        "en": "Please select a Harvey ball or check mark first.",
        "de": "Bitte zuerst einen Harvey Ball oder ein Häkchen auswählen.",
    },
    "element_unsupported": {
        "en": "This element state does not exist.",
        "de": "Diesen Zustand des Elements gibt es nicht.",
    },
    "menu_element_next": {
        "en": "Next state",
        "de": "Nächster Zustand",
    },
    "menu_harvey": {
        "en": "Filled {level} %",
        "de": "{level} % gefüllt",
    },
    "menu_check_tick": {
        "en": "Tick",
        "de": "Häkchen",
    },
    "menu_check_cross": {
        "en": "Cross",
        "de": "Kreuz",
    },
    "menu_check_empty": {
        "en": "Empty circle",
        "de": "Leerer Kreis",
    },
    "arrange_need_two": {
        "en": "Please select at least two shapes first.",
        "de": "Bitte zuerst mindestens zwei Formen auswählen.",
    },
    "arrange_need_exactly_two": {
        "en": "Please select exactly two shapes to swap.",
        "de": "Zum Tauschen bitte genau zwei Formen auswählen.",
    },
    "arrange_unsupported": {
        "en": "This arrangement does not exist.",
        "de": "Diese Anordnung gibt es nicht.",
    },
    "graphic_unsupported": {
        "en": "That graphic cannot be inserted.",
        "de": "Diese Grafik kann nicht eingefügt werden.",
    },
    "graphic_not_selected": {
        "en": "Select a LibreCharts graphic first.",
        "de": "Wählen Sie zuerst eine LibreCharts-Grafik aus.",
    },
    "menu_insert_graphic": {
        "en": "Insert graphic",
        "de": "Grafik einfügen",
    },
    "menu_insert_process": {
        "en": "Process",
        "de": "Prozess",
    },
    "menu_insert_chevron": {
        "en": "Chevron",
        "de": "Pfeilband",
    },
    "menu_insert_pyramid": {
        "en": "Pyramid",
        "de": "Pyramide",
    },
    "menu_arrange_distribute": {
        "en": "Distribute",
        "de": "Verteilen",
    },
    "menu_distribute_h_gaps": {
        "en": "Equal gaps horizontally",
        "de": "Gleiche Abstände horizontal",
    },
    "menu_distribute_h_centres": {
        "en": "Equal centres horizontally",
        "de": "Gleiche Mitten horizontal",
    },
    "menu_distribute_v_gaps": {
        "en": "Equal gaps vertically",
        "de": "Gleiche Abstände vertikal",
    },
    "menu_distribute_v_centres": {
        "en": "Equal centres vertically",
        "de": "Gleiche Mitten vertikal",
    },
    "menu_arrange_align": {
        "en": "Align",
        "de": "Ausrichten",
    },
    "menu_align_left": {
        "en": "Left edges",
        "de": "Linke Kanten",
    },
    "menu_align_right": {
        "en": "Right edges",
        "de": "Rechte Kanten",
    },
    "menu_align_top": {
        "en": "Top edges",
        "de": "Obere Kanten",
    },
    "menu_align_bottom": {
        "en": "Bottom edges",
        "de": "Untere Kanten",
    },
    "menu_align_hcenter": {
        "en": "Horizontal centres",
        "de": "Horizontale Mitten",
    },
    "menu_align_vcenter": {
        "en": "Vertical centres",
        "de": "Vertikale Mitten",
    },
    "menu_arrange_slide": {
        "en": "Align to slide",
        "de": "An der Folie ausrichten",
    },
    "menu_align_slide_left": {
        "en": "Left",
        "de": "Links",
    },
    "menu_align_slide_right": {
        "en": "Right",
        "de": "Rechts",
    },
    "menu_align_slide_top": {
        "en": "Top",
        "de": "Oben",
    },
    "menu_align_slide_bottom": {
        "en": "Bottom",
        "de": "Unten",
    },
    "menu_align_slide_hcenter": {
        "en": "Horizontal centre",
        "de": "Horizontal zentriert",
    },
    "menu_align_slide_vcenter": {
        "en": "Vertical centre",
        "de": "Vertikal zentriert",
    },
    "menu_arrange_width": {
        "en": "Same width",
        "de": "Gleiche Breite",
    },
    "menu_arrange_height": {
        "en": "Same height",
        "de": "Gleiche Höhe",
    },
    "menu_arrange_size": {
        "en": "Same size",
        "de": "Gleiche Größe",
    },
    "menu_arrange_grid": {
        "en": "Arrange in grid, {columns} columns",
        "de": "Im Raster anordnen, {columns} Spalten",
    },
    "menu_arrange_swap": {
        "en": "Swap positions",
        "de": "Positionen tauschen",
    },
    "menu_move_labels": {
        "en": "Move labels",
        "de": "Beschriftungen verschieben",
    },
    "menu_reset_labels": {
        "en": "Reset label positions",
        "de": "Beschriftungen zurücksetzen",
    },
    "menu_labels": {
        "en": "Labels",
        "de": "Beschriftungen",
    },
    "menu_legend": {
        "en": "Legend position",
        "de": "Legendenposition",
    },
    "menu_font_size": {
        "en": "Font size",
        "de": "Schriftgröße",
    },
    "menu_font_auto": {
        "en": "Automatic (scheme)",
        "de": "Automatisch (Schema)",
    },
    "menu_font_value": {
        "en": "{size} pt",
        "de": "{size} pt",
    },
    "menu_hide_label": {
        "en": "Hide label...",
        "de": "Beschriftung ausblenden...",
    },
    "menu_edit_label": {
        "en": "Change label text...",
        "de": "Beschriftungstext ändern...",
    },
    "menu_reset_label": {
        "en": "Reset label...",
        "de": "Beschriftung zurücksetzen...",
    },
    "menu_focus": {
        "en": "Focus",
        "de": "Fokus",
    },
    "menu_focus_series": {
        "en": "Series: {name}",
        "de": "Datenreihe: {name}",
    },
    "menu_focus_category": {
        "en": "Category: {name}",
        "de": "Kategorie: {name}",
    },
    "menu_focus_clear": {
        "en": "Clear focus",
        "de": "Fokus aufheben",
    },
    "menu_source": {
        "en": "Source...",
        "de": "Quelle...",
    },
    "menu_add_note": {
        "en": "Add note...",
        "de": "Hinweis hinzufügen...",
    },
    "menu_notes": {
        "en": "Notes",
        "de": "Hinweise",
    },
    "menu_remove_note": {
        "en": "Remove note",
        "de": "Hinweis entfernen",
    },
    "label_title": {
        "en": "Label",
        "de": "Beschriftung",
    },
    "label_text": {
        "en": "Text",
        "de": "Text",
    },
    "label_pick_hint": {
        "en": "Click the label to change",
        "de": "Klicken Sie die zu ändernde Beschriftung an",
    },
    "label_unsupported": {
        "en": "That label cannot be changed.",
        "de": "Diese Beschriftung kann nicht geändert werden.",
    },
    "source_title": {
        "en": "Source",
        "de": "Quelle",
    },
    "source_label": {
        "en": "Source line",
        "de": "Quellenzeile",
    },
    "note_title": {
        "en": "Note",
        "de": "Hinweis",
    },
    "note_label": {
        "en": "Text",
        "de": "Text",
    },
    "note_unsupported": {
        "en": "That note cannot be changed.",
        "de": "Dieser Hinweis kann nicht geändert werden.",
    },
    "text_empty": {
        "en": "The text must not be empty.",
        "de": "Der Text darf nicht leer sein.",
    },
    "text_too_long": {
        "en": "The text is too long (at most {limit} characters).",
        "de": "Der Text ist zu lang (höchstens {limit} Zeichen).",
    },
    "menu_legend_top": {
        "en": "Legend at the top",
        "de": "Legende oben",
    },
    "menu_legend_right": {
        "en": "Legend on the right",
        "de": "Legende rechts",
    },
    "menu_legend_bottom": {
        "en": "Legend at the bottom",
        "de": "Legende unten",
    },
    "menu_legend_left": {
        "en": "Legend on the left",
        "de": "Legende links",
    },
    "move_labels_hint": {
        "en": "Drag values and totals to move them. Esc ends.",
        "de": "Werte und Summen ziehen, um sie zu verschieben. Esc beendet.",
    },
    "deck_bad_json": {
        "en": "The deck specification is not valid JSON: {detail}",
        "de": "Die Deck-Beschreibung ist kein gültiges JSON: {detail}",
    },
    "deck_bad_spec": {
        "en": "The deck specification must be a JSON object.",
        "de": "Die Deck-Beschreibung muss ein JSON-Objekt sein.",
    },
    "deck_bad_version": {
        "en": "This deck specification has version {detail}; this LibreCharts reads version 1.",
        "de": "Diese Deck-Beschreibung hat Version {detail}; dieses LibreCharts liest Version 1.",
    },
    "deck_no_charts": {
        "en": "The deck specification contains no charts.",
        "de": "Die Deck-Beschreibung enthält keine Diagramme.",
    },
    "deck_bad_chart": {
        "en": "An entry of the deck specification is not a JSON object.",
        "de": "Ein Eintrag der Deck-Beschreibung ist kein JSON-Objekt.",
    },
    "deck_unknown_key": {
        "en": "Unknown entry {detail} in the deck specification.",
        "de": "Unbekannter Eintrag {detail} in der Deck-Beschreibung.",
    },
    "deck_no_placeholder": {
        "en": "A chart of the deck specification names no placeholder.",
        "de": "Ein Diagramm der Deck-Beschreibung nennt keinen Platzhalter.",
    },
    "deck_duplicate_placeholder": {
        "en": "The placeholder {detail} is used by more than one chart.",
        "de": "Der Platzhalter {detail} wird von mehr als einem Diagramm verwendet.",
    },
    "deck_template_missing": {
        "en": "The chart template {detail} cannot be found.",
        "de": "Die Diagrammvorlage {detail} wurde nicht gefunden.",
    },
    "deck_bad_kind": {
        "en": "Unknown chart type {detail} in the deck specification.",
        "de": "Unbekannter Diagrammtyp {detail} in der Deck-Beschreibung.",
    },
    "deck_bad_data": {
        "en": (
            "The data of the chart for placeholder {placeholder} must be a grid of at least "
            "2 x 2 cells holding numbers, text or null."
        ),
        "de": (
            "Die Daten des Diagramms für den Platzhalter {placeholder} müssen ein Raster von "
            "mindestens 2 x 2 Zellen mit Zahlen, Text oder null sein."
        ),
    },
    "deck_too_large": {
        "en": "The data of the chart for placeholder {placeholder} has more than {detail} cells.",
        "de": (
            "Die Daten des Diagramms für den Platzhalter {placeholder} haben mehr als "
            "{detail} Zellen."
        ),
    },
    "deck_invalid_chart": {
        "en": "The chart for placeholder {placeholder} is invalid: {detail}",
        "de": "Das Diagramm für den Platzhalter {placeholder} ist ungültig: {detail}",
    },
    "deck_bad_calendar": {
        "en": (
            "The working calendar of the chart for placeholder {placeholder} is invalid: {detail}"
        ),
        "de": (
            "Der Arbeitskalender des Diagramms für den Platzhalter {placeholder} ist ungültig: "
            "{detail}"
        ),
    },
    "deck_missing_placeholders": {
        "en": "The template has no placeholder for: {detail}",
        "de": "Das Template hat keinen Platzhalter für: {detail}",
    },
    "deck_duplicate_placeholders": {
        "en": "The template uses these placeholders more than once: {detail}",
        "de": "Das Template verwendet diese Platzhalter mehr als einmal: {detail}",
    },
    "deck_unused_placeholders": {
        "en": "These placeholders stayed empty: {detail}",
        "de": "Diese Platzhalter blieben leer: {detail}",
    },
    "deck_built": {
        "en": "{count} charts written to {file}.",
        "de": "{count} Diagramme in {file} geschrieben.",
    },
    "deck_built_one": {
        "en": "1 chart written to {file}.",
        "de": "1 Diagramm in {file} geschrieben.",
    },
    "deck_open_failed": {
        "en": "The template {detail} cannot be opened.",
        "de": "Das Template {detail} lässt sich nicht öffnen.",
    },
    "deck_save_failed": {
        "en": "The presentation cannot be saved as {detail}.",
        "de": "Die Präsentation lässt sich nicht als {detail} speichern.",
    },
    "deck_spec_unreadable": {
        "en": "The deck specification cannot be read: {detail}",
        "de": "Die Deck-Beschreibung lässt sich nicht lesen: {detail}",
    },
    "deck_placeholder_too_small": {
        "en": "The placeholder {detail} is too small for a chart.",
        "de": "Der Platzhalter {detail} ist zu klein für ein Diagramm.",
    },
    "deck_bad_slide": {
        "en": "The presentation has no slide {detail}.",
        "de": "Die Präsentation hat keine Folie {detail}.",
    },
    "deck_no_document": {
        "en": "No presentation was passed.",
        "de": "Es wurde keine Präsentation übergeben.",
    },
    "cli_description": {
        "en": "Build a presentation from a template and a deck specification, or update its links.",
        "de": (
            "Eine Präsentation aus Template und Deck-Beschreibung bauen oder ihre Datenlinks "
            "aktualisieren."
        ),
    },
    "cli_build": {
        "en": "fill a template with the charts of a deck specification",
        "de": "ein Template mit den Diagrammen einer Deck-Beschreibung füllen",
    },
    "cli_update": {
        "en": "update every linked chart of a presentation",
        "de": "jedes verknüpfte Diagramm einer Präsentation aktualisieren",
    },
    "cli_template": {
        "en": "template presentation with librecharts-placeholder shapes",
        "de": "Template-Präsentation mit librecharts-placeholder-Formen",
    },
    "cli_data": {
        "en": "deck specification (JSON)",
        "de": "Deck-Beschreibung (JSON)",
    },
    "cli_deck": {
        "en": "presentation whose data links are updated",
        "de": "Präsentation, deren Datenlinks aktualisiert werden",
    },
    "cli_out": {
        "en": "output file (default: save over the deck)",
        "de": "Zieldatei (Vorgabe: die Präsentation wird überschrieben)",
    },
    "cli_locale": {
        "en": "language of messages, e.g. de or en-GB (default: LibreOffice's UI locale)",
        "de": "Sprache der Meldungen, z. B. de oder en-GB (Vorgabe: UI-Sprache von LibreOffice)",
    },
    "cli_no_libreoffice": {
        "en": "LibreOffice was not found; set LIBREOFFICE_PROGRAM to its program directory.",
        "de": (
            "LibreOffice wurde nicht gefunden; LIBREOFFICE_PROGRAM auf das "
            "program-Verzeichnis setzen."
        ),
    },
    "menu_check_design": {
        "en": "Check corporate design...",
        "de": "Corporate Design prüfen...",
    },
    "design_title_load": {
        "en": "Corporate design file to check against",
        "de": "Corporate-Design-Datei für die Prüfung",
    },
    "design_load_failed": {
        "en": "The corporate design file cannot be read: {detail}",
        "de": "Die Corporate-Design-Datei lässt sich nicht lesen: {detail}",
    },
    "design_clean": {
        "en": "The presentation follows the corporate design.",
        "de": "Die Präsentation hält das Corporate Design ein.",
    },
    "design_found": {
        "en": "Deviations from the corporate design: {count}",
        "de": "Abweichungen vom Corporate Design: {count}",
    },
    "design_fixed": {
        "en": "Deviations from the corporate design fixed: {count}",
        "de": "Abweichungen vom Corporate Design korrigiert: {count}",
    },
    "design_more": {
        "en": "... and {count} more.",
        "de": "... und {count} weitere.",
    },
    "design_where_master": {
        "en": 'Master {index}, "{shape}"',
        "de": 'Master {index}, "{shape}"',
    },
    "design_where": {
        "en": "Slide {slide}, {shape}",
        "de": "Folie {slide}, {shape}",
    },
    "design_issue_scheme": {
        "en": "charts use the colour scheme {actual} instead of {expected}",
        "de": "Diagramme nutzen das Farbschema {actual} statt {expected}",
    },
    "design_issue_fill": {
        "en": "fill colour {actual} instead of {expected}",
        "de": "Füllfarbe {actual} statt {expected}",
    },
    "design_issue_line": {
        "en": "line colour {actual} instead of {expected}",
        "de": "Linienfarbe {actual} statt {expected}",
    },
    "design_issue_font": {
        "en": "font {actual} instead of {expected}",
        "de": "Schrift {actual} statt {expected}",
    },
    "design_issue_text_color": {
        "en": "text colour {actual} instead of {expected}",
        "de": "Textfarbe {actual} statt {expected}",
    },
    "design_issue_position": {
        "en": "outside the margins at {actual}, belongs at {expected}",
        "de": "außerhalb der Ränder bei {actual}, gehört nach {expected}",
    },
    "design_ask_fix": {
        "en": "Fix every deviation now? This is one undo step.",
        "de": "Alle Abweichungen jetzt korrigieren? Das ist ein Rückgängig-Schritt.",
    },
    "design_done": {
        "en": "{count} deviations fixed.",
        "de": "{count} Abweichungen korrigiert.",
    },
    "cli_check": {
        "en": "check a presentation against a corporate design file",
        "de": "eine Präsentation gegen eine Corporate-Design-Datei prüfen",
    },
    "cli_check_deck": {
        "en": "presentation to check",
        "de": "zu prüfende Präsentation",
    },
    "cli_design": {
        "en": "corporate design file (colour scheme JSON with check rules)",
        "de": "Corporate-Design-Datei (Farbschema-JSON mit Prüfregeln)",
    },
    "cli_fix": {
        "en": "fix every deviation and save the presentation",
        "de": "alle Abweichungen korrigieren und die Präsentation speichern",
    },
    "audit_clean": {
        "en": "No problems found.",
        "de": "Keine Probleme gefunden.",
    },
    "audit_summary": {
        "en": "{count} findings:",
        "de": "{count} Befunde:",
    },
    "audit_line": {
        "en": "Slide {slide}: {message}",
        "de": "Folie {slide}: {message}",
    },
    "audit_corrupt_chart": {
        "en": "The chart data are unreadable. {detail}",
        "de": "Die Diagrammdaten sind unlesbar. {detail}",
    },
    "audit_linked": {
        "en": "The chart is linked to an external source.",
        "de": "Das Diagramm ist mit einer externen Quelle verknüpft.",
    },
    "audit_stale_link": {
        "en": "The linked source {detail} changed since the last update.",
        "de": "Die verknüpfte Quelle {detail} hat sich seit der letzten Aktualisierung geändert.",
    },
    "audit_design": {
        "en": "Corporate design deviation: {detail}",
        "de": "Abweichung vom Corporate Design: {detail}",
    },
    "alt_graphic": {
        "en": "LibreCharts graphic: {kind} {name}",
        "de": "LibreCharts-Grafik: {kind} {name}",
    },
    "alt_harvey": {
        "en": "Harvey ball {level} %",
        "de": "Harvey-Ball {level} %",
    },
    "alt_check_tick": {
        "en": "Check mark: yes",
        "de": "Häkchen: ja",
    },
    "alt_check_cross": {
        "en": "Check mark: no",
        "de": "Kreuz: nein",
    },
    "alt_check_empty": {
        "en": "Check mark: empty",
        "de": "Häkchen: leer",
    },
    "colorblind_unknown": {
        "en": "That colour-blindness simulation is not known.",
        "de": "Diese Farbsehschwäche-Simulation ist unbekannt.",
    },
    "menu_colorblind": {
        "en": "Colour-blind simulation",
        "de": "Farbsehschwäche-Simulation",
    },
    "menu_deuteranopia": {
        "en": "Deuteranopia",
        "de": "Deuteranopie",
    },
    "menu_protanopia": {
        "en": "Protanopia",
        "de": "Protanopie",
    },
    "menu_tritanopia": {
        "en": "Tritanopia",
        "de": "Tritanopie",
    },
    "menu_audit": {
        "en": "Audit presentation...",
        "de": "Präsentation prüfen...",
    },
    "spec_exported": {
        "en": "{count} charts exported.",
        "de": "{count} Diagramme exportiert.",
    },
    "spec_export_failed": {
        "en": "The specification cannot be written: {detail}",
        "de": "Die Spezifikation lässt sich nicht schreiben: {detail}",
    },
    "menu_export_spec": {
        "en": "Export deck specification...",
        "de": "Deck-Spezifikation exportieren...",
    },
    "menu_import_data": {
        "en": "Import data...",
        "de": "Daten importieren...",
    },
    "menu_insert_from_clipboard": {
        "en": "Chart from clipboard",
        "de": "Diagramm aus Zwischenablage",
    },
    "menu_save_template": {
        "en": "Save chart as template...",
        "de": "Diagramm als Vorlage speichern...",
    },
    "menu_insert_template": {
        "en": "Insert from template",
        "de": "Aus Vorlage einfügen",
    },
    "template_save_title": {
        "en": "Save chart as template",
        "de": "Diagramm als Vorlage speichern",
    },
    "template_name": {
        "en": "Name",
        "de": "Name",
    },
    "template_saved": {
        "en": "Template saved to {path}.",
        "de": "Vorlage nach {path} gespeichert.",
    },
    "template_save_failed": {
        "en": "The template cannot be saved: {detail}",
        "de": "Die Vorlage lässt sich nicht speichern: {detail}",
    },
    "template_missing": {
        "en": "No template called {name}.",
        "de": "Keine Vorlage namens {name}.",
    },
    "template_load_failed": {
        "en": "The template cannot be read: {detail}",
        "de": "Die Vorlage lässt sich nicht lesen: {detail}",
    },
    "menu_export_csv": {
        "en": "Export chart data as CSV...",
        "de": "Diagrammdaten als CSV exportieren...",
    },
    "csv_title_save": {
        "en": "Export chart data",
        "de": "Diagrammdaten exportieren",
    },
    "csv_filter": {
        "en": "CSV file",
        "de": "CSV-Datei",
    },
    "csv_exported": {
        "en": "Chart data exported to {path}.",
        "de": "Diagrammdaten nach {path} exportiert.",
    },
    "csv_export_failed": {
        "en": "The chart data cannot be exported: {detail}",
        "de": "Die Diagrammdaten lassen sich nicht exportieren: {detail}",
    },
    "menu_patterns_show": {
        "en": "Show patterns",
        "de": "Muster zeigen",
    },
    "menu_patterns_hide": {
        "en": "Hide patterns",
        "de": "Muster ausblenden",
    },
    "alt_summary": {
        "en": "{kind} with {categories} categories and {series} series.",
        "de": "{kind} mit {categories} Kategorien und {series} Datenreihen.",
    },
    "alt_steps": {
        "en": "{kind} with {count} steps.",
        "de": "{kind} mit {count} Schritten.",
    },
    "alt_points": {
        "en": "{kind} with {count} points.",
        "de": "{kind} mit {count} Punkten.",
    },
    "alt_rows": {
        "en": "{kind} with {count} rows.",
        "de": "{kind} mit {count} Zeilen.",
    },
    "alt_size": {
        "en": "size {size}",
        "de": "Größe {size}",
    },
    "alt_milestone": {
        "en": "milestone on {date}",
        "de": "Meilenstein am {date}",
    },
    "alt_range": {
        "en": "{start} to {end}",
        "de": "{start} bis {end}",
    },
    "alt_empty": {
        "en": "no value",
        "de": "kein Wert",
    },
    "alt_no_data": {
        "en": "{kind} without data.",
        "de": "{kind} ohne Daten.",
    },
    "alt_source": {
        "en": "Source: {source}.",
        "de": "Quelle: {source}.",
    },
    "alt_axis": {
        "en": "Axis title: {title}.",
        "de": "Achsentitel: {title}.",
    },
    "alt_trend": {
        "en": "Trendline for series {series} ({kind}).",
        "de": "Trendlinie für Datenreihe {series} ({kind}).",
    },
    "kind_table": {
        "en": "Table",
        "de": "Tabelle",
    },
    "kind_matrix": {
        "en": "2x2 matrix",
        "de": "2x2-Matrix",
    },
    "insert_table": {
        "en": "Table",
        "de": "Tabelle",
    },
    "insert_matrix": {
        "en": "2x2 matrix",
        "de": "2x2-Matrix",
    },
    "kind_pareto": {
        "en": "Pareto chart",
        "de": "Pareto-Diagramm",
    },
    "kind_dumbbell": {
        "en": "Dumbbell chart",
        "de": "Hanteldiagramm",
    },
    "kind_bullet": {
        "en": "Bullet chart",
        "de": "Bullet-Diagramm",
    },
    "kind_funnel": {
        "en": "Funnel chart",
        "de": "Trichterdiagramm",
    },
    "kind_boxplot": {
        "en": "Box plot",
        "de": "Boxplot",
    },
    "insert_dumbbell": {
        "en": "Dumbbell",
        "de": "Hantel",
    },
    "insert_bullet": {
        "en": "Bullet",
        "de": "Bullet",
    },
    "insert_funnel": {
        "en": "Funnel",
        "de": "Trichter",
    },
    "insert_boxplot": {
        "en": "Box plot",
        "de": "Boxplot",
    },
    "menu_pareto": {
        "en": "Show as Pareto chart",
        "de": "Als Pareto-Diagramm zeigen",
    },
    "menu_pareto_off": {
        "en": "Show as normal chart",
        "de": "Als normales Diagramm zeigen",
    },
    "menu_dumbbell_horizontal": {
        "en": "Horizontal",
        "de": "Horizontal",
    },
    "menu_dumbbell_vertical": {
        "en": "Vertical",
        "de": "Vertikal",
    },
    "bullet_invalid": {
        "en": "The bullet data sheet is invalid.",
        "de": "Das Bullet-Datenblatt ist ungültig.",
    },
    "bullet_missing": {
        "en": "A bullet row needs an actual value and a maximum.",
        "de": "Eine Bullet-Zeile braucht einen Ist-Wert und ein Maximum.",
    },
    "bullet_negative": {
        "en": "A bullet chart cannot show negative values or a maximum of zero.",
        "de": "Ein Bullet-Diagramm kann keine negativen Werte oder ein Maximum von null zeigen.",
    },
    "bullet_empty": {
        "en": "The bullet data sheet has no rows.",
        "de": "Das Bullet-Datenblatt hat keine Zeilen.",
    },
    "boxplot_invalid": {
        "en": "The box plot data sheet is invalid.",
        "de": "Das Boxplot-Datenblatt ist ungültig.",
    },
    "boxplot_incomplete": {
        "en": "A box plot row needs Min, Q1, Median, Q3 and Max.",
        "de": "Eine Boxplot-Zeile braucht Min, Q1, Median, Q3 und Max.",
    },
    "boxplot_order": {
        "en": "A box plot needs Min <= Q1 <= Median <= Q3 <= Max.",
        "de": "Ein Boxplot braucht Min <= Q1 <= Median <= Q3 <= Max.",
    },
    "boxplot_empty": {
        "en": "The box plot data sheet has no rows.",
        "de": "Das Boxplot-Datenblatt hat keine Zeilen.",
    },
    "trend_linear": {
        "en": "linear",
        "de": "linear",
    },
    "trend_exponential": {
        "en": "exponential",
        "de": "exponentiell",
    },
    "menu_axis_dialog": {
        "en": "Axes...",
        "de": "Achsen...",
    },
    "menu_trendlines": {
        "en": "Trendlines",
        "de": "Trendlinien",
    },
    "menu_add_trendline": {
        "en": "Add trendline...",
        "de": "Trendlinie hinzufügen...",
    },
    "menu_remove_trendline": {
        "en": "Remove trendline",
        "de": "Trendlinie entfernen",
    },
    "axis_title": {
        "en": "Value axis",
        "de": "Werteachse",
    },
    "axis_min_label": {
        "en": "Minimum",
        "de": "Minimum",
    },
    "axis_max_label": {
        "en": "Maximum",
        "de": "Maximum",
    },
    "axis_step_label": {
        "en": "Step",
        "de": "Schritt",
    },
    "axis_scale_label": {
        "en": "Scale",
        "de": "Skala",
    },
    "axis_scale_linear": {
        "en": "Linear",
        "de": "Linear",
    },
    "axis_scale_log": {
        "en": "Logarithmic",
        "de": "Logarithmisch",
    },
    "category_axis_title": {
        "en": "Category axis",
        "de": "Kategorieachse",
    },
    "trend_title": {
        "en": "Trendline",
        "de": "Trendlinie",
    },
    "trend_series": {
        "en": "Series",
        "de": "Datenreihe",
    },
    "trend_kind": {
        "en": "Kind",
        "de": "Art",
    },
    "trend_forecast": {
        "en": "Forecast (periods)",
        "de": "Prognose (Perioden)",
    },
    "trend_show_r2": {
        "en": "Show R²",
        "de": "R² anzeigen",
    },
    "trend_show_equation": {
        "en": "Show equation",
        "de": "Gleichung anzeigen",
    },
    "trend_invalid": {
        "en": "The trendline cannot be fitted to this data.",
        "de": "Die Trendlinie kann nicht an diese Daten angepasst werden.",
    },
    "axis_invalid": {
        "en": "The axis values are not valid.",
        "de": "Die Achsenwerte sind ungültig.",
    },
    "axis_cut_warning": {
        "en": "Bars will be cut: readers may misread the chart. Continue?",
        "de": "Die Balken werden abgeschnitten: Leser könnten das Diagramm "
        "falsch deuten. Fortfahren?",
    },
    "alt_note": {
        "en": "Note: {text}.",
        "de": "Hinweis: {text}.",
    },
    "addon_insert_column": {
        "en": "Insert column chart",
        "de": "Säulendiagramm einfügen",
    },
    "addon_insert_bar": {
        "en": "Insert bar chart",
        "de": "Balkendiagramm einfügen",
    },
    "addon_insert_waterfall": {
        "en": "Insert waterfall chart",
        "de": "Wasserfalldiagramm einfügen",
    },
    "addon_insert_mekko": {
        "en": "Insert Marimekko chart",
        "de": "Marimekko-Diagramm einfügen",
    },
    "addon_insert_line": {
        "en": "Insert line chart",
        "de": "Liniendiagramm einfügen",
    },
    "addon_insert_area": {
        "en": "Insert area chart",
        "de": "Flächendiagramm einfügen",
    },
    "addon_insert_pie": {
        "en": "Insert pie chart",
        "de": "Kreisdiagramm einfügen",
    },
    "addon_insert_scatter": {
        "en": "Insert scatter chart",
        "de": "Streudiagramm einfügen",
    },
    "addon_insert_butterfly": {
        "en": "Insert butterfly chart",
        "de": "Schmetterlingsdiagramm einfügen",
    },
    "addon_insert_gantt": {
        "en": "Insert Gantt chart",
        "de": "Gantt-Diagramm einfügen",
    },
    "addon_insert_dumbbell": {
        "en": "Insert dumbbell chart",
        "de": "Hanteldiagramm einfügen",
    },
    "addon_insert_bullet": {
        "en": "Insert bullet chart",
        "de": "Bullet-Diagramm einfügen",
    },
    "addon_insert_funnel": {
        "en": "Insert funnel chart",
        "de": "Trichterdiagramm einfügen",
    },
    "addon_insert_boxplot": {
        "en": "Insert box plot",
        "de": "Boxplot einfügen",
    },
    "addon_insert_table": {
        "en": "Insert table",
        "de": "Tabelle einfügen",
    },
    "addon_insert_matrix": {
        "en": "Insert 2x2 matrix",
        "de": "2x2-Matrix einfügen",
    },
    "addon_working_days": {
        "en": "Working days...",
        "de": "Arbeitstage...",
    },
    "addon_import_csv": {
        "en": "Import from CSV...",
        "de": "Aus CSV importieren...",
    },
    "addon_import_project": {
        "en": "Import from ProjectLibre...",
        "de": "Aus ProjectLibre importieren...",
    },
    "addon_insert_harvey": {
        "en": "Insert Harvey ball",
        "de": "Harvey Ball einfügen",
    },
    "addon_insert_check": {
        "en": "Insert check mark",
        "de": "Häkchen einfügen",
    },
    "addon_element_next": {
        "en": "Next state of Harvey ball or check mark",
        "de": "Nächster Zustand von Harvey Ball oder Häkchen",
    },
}

# The message of every add-on menu and toolbar entry (extension/Addons.xcu), by its command.
# The build writes their translations into the package (scripts/build_oxt.py, ADR 0031).
ADDON_KEYS: dict[str, str] = {
    "EditData": "menu_edit_data",
    "LinkData": "menu_link_data",
    "UpdateAllLinks": "menu_update_all_links",
    "SameScale": "menu_same_scale",
    "RemoveSameScale": "menu_remove_same_scale",
    "CopyChartFormat": "menu_copy_format",
    "ApplyChartFormat": "menu_apply_format",
    "MoveLabels": "menu_move_labels",
    "ResetLabels": "menu_reset_labels",
    "PickAnnotation?kind=difference": "menu_add_difference",
    "PickAnnotation?kind=difference&style=level": "menu_add_level",
    "PickAnnotation?kind=cagr": "menu_add_cagr",
    "AxisBreak": "menu_add_break",
    "Arrange?op=width": "menu_arrange_width",
    "Arrange?op=height": "menu_arrange_height",
    "Arrange?op=size": "menu_arrange_size",
    "Arrange?op=swap": "menu_arrange_swap",
    "InsertAgenda": "menu_insert_agenda",
    "StartChapter": "menu_start_chapter",
    "UpdateAgenda": "menu_update_agenda",
    "ExportCsv": "menu_export_csv",
    "CheckDesign": "menu_check_design",
    "InsertColumnChart": "addon_insert_column",
    "InsertBarChart": "addon_insert_bar",
    "InsertWaterfallChart": "addon_insert_waterfall",
    "InsertMekkoChart": "addon_insert_mekko",
    "InsertLineChart": "addon_insert_line",
    "InsertAreaChart": "addon_insert_area",
    "InsertPieChart": "addon_insert_pie",
    "InsertScatterChart": "addon_insert_scatter",
    "InsertButterflyChart": "addon_insert_butterfly",
    "InsertGanttChart": "addon_insert_gantt",
    "InsertDumbbellChart": "addon_insert_dumbbell",
    "InsertBulletChart": "addon_insert_bullet",
    "InsertFunnelChart": "addon_insert_funnel",
    "InsertBoxplotChart": "addon_insert_boxplot",
    "InsertTableChart": "addon_insert_table",
    "InsertMatrixChart": "addon_insert_matrix",
    "WorkingDays": "addon_working_days",
    "ImportGanttCsv": "addon_import_csv",
    "ImportGanttProject": "addon_import_project",
    "InsertElement?harvey=50": "addon_insert_harvey",
    "InsertElement?check=tick": "addon_insert_check",
    "SetElement?next=1": "addon_element_next",
}
ADDON_GRID = "Arrange?op=grid&columns="  # + the number of columns: menu_arrange_grid


def language(locale: str) -> str:
    """The language of a LibreOffice locale like ``de-DE`` or ``pt_BR``: ``de``, ``pt``."""
    return re.split(r"[-_]", locale.strip(), maxsplit=1)[0].lower()


def text(key: str, locale: str, **fields: str) -> str:
    """The message ``key`` for a LibreOffice locale like ``de-DE``; English if unsupported."""
    wanted = language(locale)
    table = MESSAGES[key]
    message = table.get(wanted) or translations(wanted).get(key) or table[FALLBACK_LANGUAGE]
    return message.format(**fields)


@cache
def translations(code: str) -> dict[str, str]:
    """The messages of ``locales/<code>.json``; empty for English, German and unknown languages.

    A file that cannot be read or holds anything but strings counts as missing, so a broken
    translation falls back to English instead of breaking the extension.
    """
    if code in SOURCE_LANGUAGES or not code.isalpha():
        return {}
    try:
        raw: object = json.loads((LOCALES / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    entries = cast("dict[object, object]", raw)
    return {
        key: value
        for key, value in entries.items()
        if isinstance(key, str) and isinstance(value, str) and value and key in MESSAGES
    }


def languages() -> tuple[str, ...]:
    """Every language with messages: English, German and each file in ``locales/``."""
    found = sorted(
        path.stem for path in LOCALES.glob("*.json") if path.stem not in SOURCE_LANGUAGES
    )
    return (*SOURCE_LANGUAGES, *found)


def source(code: str) -> dict[str, str]:
    """English or German as a flat key -> text mapping, the content of ``locales/<code>.json``."""
    return {key: table[code] for key, table in sorted(MESSAGES.items())}


def addon_title(command: str, locale: str) -> str | None:
    """The title of the add-on entry dispatching ``command`` (without ``org.librecharts:``)."""
    key = ADDON_KEYS.get(command)
    if key is not None:
        return text(key, locale)
    if command.startswith(ADDON_GRID):
        return text("menu_arrange_grid", locale, columns=command.removeprefix(ADDON_GRID))
    return None
