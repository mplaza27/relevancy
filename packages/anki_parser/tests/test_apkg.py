"""Integration tests for parse_apkg against the AnKing deck.

Requires: anking/AnKing Step Deck.apkg (5.6GB) to be present.
Skipped automatically if the file is not found.
"""

from pathlib import Path

import pytest

APKG_PATH = Path(__file__).parents[3] / "anking" / "AnKing Step Deck.apkg"

pytestmark = pytest.mark.skipif(
    not APKG_PATH.exists(),
    reason=f"AnKing deck not found at {APKG_PATH}",
)


@pytest.fixture(scope="module")
def collection():
    from anki_parser import parse_apkg

    return parse_apkg(APKG_PATH)


def test_note_count(collection):
    assert len(collection.notes) == 28660


def test_card_count(collection):
    assert len(collection.cards) == 35079


def test_notetype_count(collection):
    assert len(collection.notetypes) >= 2


def test_notetype_names(collection):
    names = {nt.name for nt in collection.notetypes.values()}
    assert any("AnKingOverhaul" in n for n in names), f"Expected AnKingOverhaul in {names}"
    assert any("IO" in n for n in names), f"Expected IO notetype in {names}"


def test_ankingoverhall_fields(collection):
    for nt in collection.notetypes.values():
        if "AnKingOverhaul" in nt.name:
            field_names = nt.field_names
            assert "Text" in field_names, f"Expected 'Text' field, got {field_names}"
            break


def test_sample_note_has_tags(collection):
    note = next(iter(collection.notes.values()))
    # Tags list should exist (may be empty for some notes)
    assert isinstance(note.tags, list)


def test_sample_note_has_fields(collection):
    for note in collection.notes.values():
        assert isinstance(note.field_values, dict)
        assert len(note.field_values) > 0
        break


def test_media_map_exists(collection):
    # AnKing deck has ~40,570 media files
    assert len(collection.media_map) > 0


def test_clean_field_extraction(collection):
    from anki_parser.text import extract_clean_text

    for nt in collection.notetypes.values():
        if "AnKingOverhaul" in nt.name:
            for note in collection.notes.values():
                if note.notetype_id == nt.id:
                    text_field = note.get_field("Text")
                    if text_field:
                        clean = extract_clean_text(text_field)
                        assert isinstance(clean, str)
                        return
    pytest.skip("Could not find AnKingOverhaul note with Text field")


def test_deck_for_card(collection):
    card = next(iter(collection.cards.values()))
    deck = collection.deck_for_card(card)
    assert deck is not None
    assert isinstance(deck.name, str)


def test_cards_for_note(collection):
    note = next(iter(collection.notes.values()))
    cards = collection.cards_for_note(note.id)
    assert len(cards) >= 1
