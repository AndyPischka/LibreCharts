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
    "pick_break": {
        "en": "Click the column to shorten with an axis break. Esc cancels.",
        "de": "Säule anklicken, die mit einem Achsenbruch gekürzt wird. Esc bricht ab.",
    },
    "corrupt_chart": {
        "en": "The data of this chart cannot be read: {detail}",
        "de": "Die Daten dieses Diagramms können nicht gelesen werden: {detail}",
    },
}


def text(key: str, locale: str, **fields: str) -> str:
    """The message ``key`` for a LibreOffice locale like ``de-DE``; English if unsupported."""
    language = locale.split("-")[0].lower()
    table = MESSAGES[key]
    return table.get(language, table[FALLBACK_LANGUAGE]).format(**fields)
