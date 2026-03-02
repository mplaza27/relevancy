from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class CardType(IntEnum):
    NEW = 0
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3


class CardQueue(IntEnum):
    MANUALLY_BURIED = -3
    SIBLING_BURIED = -2
    SUSPENDED = -1
    NEW = 0
    LEARNING = 1
    REVIEW = 2
    DAY_LEARN_RELEARN = 3
    PREVIEW = 4


@dataclass(frozen=True, slots=True)
class FieldDef:
    notetype_id: int
    ordinal: int
    name: str


@dataclass(frozen=True, slots=True)
class TemplateDef:
    notetype_id: int
    ordinal: int
    name: str


@dataclass(frozen=True, slots=True)
class NoteType:
    id: int
    name: str
    fields: tuple[FieldDef, ...]
    templates: tuple[TemplateDef, ...]

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    @property
    def is_cloze(self) -> bool:
        return "cloze" in self.name.lower()


@dataclass(frozen=True, slots=True)
class Deck:
    id: int
    name: str  # hierarchical with "::" separator

    @property
    def parts(self) -> list[str]:
        return self.name.split("::")

    @property
    def leaf_name(self) -> str:
        return self.parts[-1]


@dataclass(frozen=True, slots=True)
class Tag:
    name: str


@dataclass(slots=True)
class Note:
    id: int
    guid: str
    notetype_id: int
    modification_time: int
    tags: list[str]
    field_values: dict[str, str]  # {field_name: raw_html_value}

    def get_field(self, name: str) -> str:
        """Return the raw HTML value of a field by name."""
        return self.field_values.get(name, "")

    def get_clean_field(self, name: str) -> str:
        """Return cleaned plain-text value of a field."""
        from anki_parser.text import extract_clean_text

        return extract_clean_text(self.field_values.get(name, ""))


@dataclass(frozen=True, slots=True)
class Card:
    id: int
    note_id: int
    deck_id: int
    ordinal: int
    modification_time: int
    card_type: CardType
    queue: CardQueue
    due: int
    interval: int
    ease_factor: int
    review_count: int
    lapse_count: int
    flags: int


@dataclass
class AnkiCollection:
    notetypes: dict[int, NoteType]
    decks: dict[int, Deck]
    notes: dict[int, Note]
    cards: dict[int, Card]
    tags: list[Tag]
    media_map: dict[str, str]  # {"0": "image.png", ...}

    def notes_by_notetype(self, name: str) -> list[Note]:
        """Return all notes whose notetype name matches (case-insensitive substring)."""
        target = name.lower()
        matching_ids = {nt_id for nt_id, nt in self.notetypes.items() if target in nt.name.lower()}
        return [n for n in self.notes.values() if n.notetype_id in matching_ids]

    def cards_for_note(self, note_id: int) -> list[Card]:
        """Return all cards associated with a note."""
        return [c for c in self.cards.values() if c.note_id == note_id]

    def deck_for_card(self, card: Card) -> Deck | None:
        """Return the deck for a card, or None if not found."""
        return self.decks.get(card.deck_id)
