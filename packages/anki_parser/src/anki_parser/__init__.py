"""anki_parser — standalone read-only parser for Anki .apkg files."""

__version__ = "0.1.0"

from anki_parser.apkg import parse_apkg
from anki_parser.media import extract_media_files
from anki_parser.models import (
    AnkiCollection,
    Card,
    CardQueue,
    CardType,
    Deck,
    FieldDef,
    Note,
    NoteType,
    Tag,
    TemplateDef,
)
from anki_parser.text import (
    extract_clean_text,
    extract_image_refs,
    extract_sound_refs,
    is_meaningful_field,
    strip_cloze,
    strip_html,
    strip_sound_refs,
)

__all__ = [
    # Entry points
    "parse_apkg",
    "extract_media_files",
    # Models
    "AnkiCollection",
    "Card",
    "CardQueue",
    "CardType",
    "Deck",
    "FieldDef",
    "Note",
    "NoteType",
    "Tag",
    "TemplateDef",
    # Text utilities
    "extract_clean_text",
    "extract_image_refs",
    "extract_sound_refs",
    "is_meaningful_field",
    "strip_cloze",
    "strip_html",
    "strip_sound_refs",
]
