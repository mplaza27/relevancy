[x]
# Prompt 02: Anki Parser Package

## Goal
Build the standalone `anki_parser` Python package that reads `.apkg` files and extracts all note/card/deck/tag data. This package must be self-contained and transferable to the `pro-me` project.

## Context
- Location: `packages/anki_parser/src/anki_parser/`
- Dependencies: `zstandard`, `selectolax` (only two external deps)
- Test with: `anking/AnKing Step Deck.apkg` (28,660 notes, 35,079 cards, ~40,570 media files)
- The `.apkg` is a ZIP containing `collection.anki21b` (zstd-compressed SQLite)
- SQLite requires custom `unicase` collation registration
- Fields in `notes.flds` are separated by `\x1f` (unit separator)
- Fields contain HTML, `<img>` tags, `[sound:...]` refs, and `{{c1::...}}` cloze syntax

## Files to Implement

### 1. `models.py` — Data classes
Define using `dataclasses` (not Pydantic — no validation overhead needed for trusted SQLite data):

```python
from dataclasses import dataclass
from enum import IntEnum

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
    # Properties: field_names, is_cloze

@dataclass(frozen=True, slots=True)
class Deck:
    id: int
    name: str  # hierarchical with "::" separator
    # Properties: parts, leaf_name

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
    # Methods: get_field(name), get_clean_field(name)

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
    # Methods: notes_by_notetype(name), cards_for_note(note_id), deck_for_card(card)
```

### 2. `text.py` — HTML stripping and text extraction
Use `selectolax` with lexbor backend for fast HTML parsing:

- `strip_cloze(text)` — Replace `{{c1::answer::hint}}` with `answer` using regex `r"\{\{c\d+::(.*?)(?:::[^}]*)?\}\}"`
- `strip_sound_refs(text)` — Remove `[sound:filename.mp3]` patterns
- `extract_image_refs(html)` — Return list of image filenames from `<img src="...">` tags
- `extract_sound_refs(html)` — Return list of sound filenames from `[sound:...]`
- `strip_html(html)` — Convert `<br>` to newlines, remove tags, collapse whitespace. Use selectolax for speed.
- `extract_clean_text(html)` — Full pipeline: strip_cloze → strip_sound_refs → strip_html → clean
- `is_meaningful_field(html)` — Return False for empty/whitespace-only fields

Handle nested cloze edge case: `{{c1::{{c2::text}}}}` — process iteratively until stable.

### 3. `database.py` — SQLite connection and data loading
- `register_unicase(conn)` — Register the `unicase` collation: `lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())`
- `open_anki_db(db_bytes)` — Context manager: write bytes to temp file, connect, register collation, yield conn, cleanup
- `load_collection(conn, media_map)` — Read all tables and build `AnkiCollection`:
  1. Load notetypes + fields + templates
  2. Load decks
  3. Load notes: split `flds` by `\x1f`, map to field names from notetype
  4. Load cards
  5. Load tags
  6. Return `AnkiCollection`

### 4. `apkg.py` — ZIP extraction and top-level entry point
- `parse_apkg(path)` — Main entry point. Opens ZIP, detects format, extracts DB, parses media map, loads collection.
- Format detection:
  - `collection.anki21b` → zstd-compressed (decompress with `zstandard`)
  - `collection.anki21` → plain SQLite
  - `collection.anki2` → legacy SQLite
- `_extract_media_map(zf)` — Parse the `media` file as JSON (try JSON first, it works for most exports including this AnKing deck)

### 5. `media.py` — Media file extraction
- `extract_media_files(apkg_path, output_dir)` — Extract numbered media files from ZIP to output directory, renaming from numeric names to original filenames using the media map
- Not critical for MVP but useful for completeness

### 6. `__init__.py` — Public API
Export: `parse_apkg`, all model classes, all text utility functions. Set `__version__ = "0.1.0"`.

## Testing
Write tests in `packages/anki_parser/tests/`:

- `test_text.py`:
  - Test `strip_cloze` with simple, nested, and hint cases
  - Test `strip_html` with `<br>`, `<div>`, `<img>`, nested tags
  - Test `extract_image_refs` and `extract_sound_refs`
  - Test `extract_clean_text` full pipeline
  - Test `is_meaningful_field` with empty, whitespace, and real content

- `test_apkg.py` (integration test if apkg available):
  - Parse the AnKing deck
  - Verify note count = 28,660
  - Verify card count = 35,079
  - Verify 2 note types: AnKingOverhaul and IO-one by one
  - Verify field names match expected for each notetype
  - Verify a sample note has correct tags and fields

## Verification
```python
from anki_parser import parse_apkg

collection = parse_apkg("anking/AnKing Step Deck.apkg")
assert len(collection.notes) == 28660
assert len(collection.cards) == 35079
assert len(collection.notetypes) >= 2

# Check a note
note = list(collection.notes.values())[0]
print(note.get_clean_field("Text"))
print(note.tags[:3])
```
