from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

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


def register_unicase(conn: sqlite3.Connection) -> None:
    """Register the unicase collation required by Anki schema v15+."""
    conn.create_collation(
        "unicase",
        lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()),
    )


@contextmanager
def open_anki_db(db_bytes: bytes) -> Generator[sqlite3.Connection, None, None]:
    """Write db_bytes to a temp file, open SQLite connection, register unicase, yield."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(db_bytes)

    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.row_factory = sqlite3.Row
        register_unicase(conn)
        try:
            yield conn
        finally:
            conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)


def _load_notetypes(conn: sqlite3.Connection) -> dict[int, NoteType]:
    """Load notetypes with their fields and templates from the notetypes/fields/templates tables."""
    notetypes: dict[int, NoteType] = {}
    fields_by_notetype: dict[int, list[FieldDef]] = {}
    templates_by_notetype: dict[int, list[TemplateDef]] = {}

    # Try modern schema (Anki 2.1.28+)
    names_by_id: dict[int, str] = {}

    try:
        cursor = conn.execute("SELECT id, name FROM notetypes ORDER BY id")
        rows = cursor.fetchall()
        if not rows:
            raise ValueError("Empty notetypes table")

        for row in rows:
            nt_id = row["id"]
            names_by_id[nt_id] = row["name"]
            fields_by_notetype[nt_id] = []
            templates_by_notetype[nt_id] = []

        # Load fields
        for row in conn.execute("SELECT ntid, ord, name FROM fields ORDER BY ntid, ord"):
            fd = FieldDef(notetype_id=row["ntid"], ordinal=row["ord"], name=row["name"])
            fields_by_notetype.setdefault(row["ntid"], []).append(fd)

        # Load templates
        for row in conn.execute("SELECT ntid, ord, name FROM templates ORDER BY ntid, ord"):
            td = TemplateDef(notetype_id=row["ntid"], ordinal=row["ord"], name=row["name"])
            templates_by_notetype.setdefault(row["ntid"], []).append(td)

        return {
            nt_id: NoteType(
                id=nt_id,
                name=nt_name,
                fields=tuple(fields_by_notetype.get(nt_id, [])),
                templates=tuple(templates_by_notetype.get(nt_id, [])),
            )
            for nt_id, nt_name in names_by_id.items()
        }

    except (sqlite3.OperationalError, ValueError):
        # Fall back to legacy col table with JSON models
        return _load_notetypes_legacy(conn)


def _load_notetypes_legacy(conn: sqlite3.Connection) -> dict[int, NoteType]:
    """Load notetypes from the legacy col.models JSON blob."""
    row = conn.execute("SELECT models FROM col").fetchone()
    if not row:
        return {}

    models_json: dict = json.loads(row["models"])
    notetypes: dict[int, NoteType] = {}

    for nt_id_str, model in models_json.items():
        nt_id = int(nt_id_str)
        nt_name = model.get("name", "")

        flds_raw = model.get("flds", [])
        fields = tuple(
            FieldDef(notetype_id=nt_id, ordinal=f.get("ord", i), name=f.get("name", ""))
            for i, f in enumerate(flds_raw)
        )

        tmpls_raw = model.get("tmpls", [])
        templates = tuple(
            TemplateDef(notetype_id=nt_id, ordinal=t.get("ord", i), name=t.get("name", ""))
            for i, t in enumerate(tmpls_raw)
        )

        notetypes[nt_id] = NoteType(id=nt_id, name=nt_name, fields=fields, templates=templates)

    return notetypes


def _load_decks(conn: sqlite3.Connection) -> dict[int, Deck]:
    """Load decks. Tries modern table, falls back to col.decks JSON."""
    decks: dict[int, Deck] = {}

    try:
        rows = conn.execute("SELECT id, name FROM decks ORDER BY id").fetchall()
        if not rows:
            raise ValueError("Empty decks table")
        for row in rows:
            deck_id = row["id"]
            decks[deck_id] = Deck(id=deck_id, name=row["name"])
        return decks
    except (sqlite3.OperationalError, ValueError):
        pass

    # Legacy: parse col.decks JSON
    row = conn.execute("SELECT decks FROM col").fetchone()
    if not row:
        return {}

    decks_json: dict = json.loads(row["decks"])
    for deck_id_str, deck_data in decks_json.items():
        if deck_id_str == "1":
            continue  # Skip default deck placeholder
        deck_id = int(deck_id_str)
        decks[deck_id] = Deck(id=deck_id, name=deck_data.get("name", ""))

    return decks


def _load_notes(
    conn: sqlite3.Connection, notetypes: dict[int, NoteType]
) -> dict[int, Note]:
    """Load all notes, mapping field values by field name."""
    notes: dict[int, Note] = {}

    rows = conn.execute(
        "SELECT id, guid, mid, mod, tags, flds FROM notes ORDER BY id"
    ).fetchall()

    for row in rows:
        note_id = row["id"]
        notetype_id = row["mid"]
        raw_flds = row["flds"]
        values = raw_flds.split("\x1f")

        # Build field_values dict using notetype field names
        nt = notetypes.get(notetype_id)
        if nt:
            field_names = nt.field_names
            field_values = {
                field_names[i] if i < len(field_names) else f"field_{i}": v
                for i, v in enumerate(values)
            }
        else:
            field_values = {f"field_{i}": v for i, v in enumerate(values)}

        # Parse tags: space-separated string with leading/trailing spaces
        tags_str = row["tags"].strip()
        tags = tags_str.split() if tags_str else []

        notes[note_id] = Note(
            id=note_id,
            guid=row["guid"],
            notetype_id=notetype_id,
            modification_time=row["mod"],
            tags=tags,
            field_values=field_values,
        )

    return notes


def _load_cards(conn: sqlite3.Connection) -> dict[int, Card]:
    """Load all cards."""
    cards: dict[int, Card] = {}

    rows = conn.execute(
        "SELECT id, nid, did, ord, mod, type, queue, due, ivl, factor, reps, lapses, flags "
        "FROM cards ORDER BY id"
    ).fetchall()

    for row in rows:
        card_id = row["id"]
        cards[card_id] = Card(
            id=card_id,
            note_id=row["nid"],
            deck_id=row["did"],
            ordinal=row["ord"],
            modification_time=row["mod"],
            card_type=CardType(row["type"]),
            queue=CardQueue(row["queue"]),
            due=row["due"],
            interval=row["ivl"],
            ease_factor=row["factor"],
            review_count=row["reps"],
            lapse_count=row["lapses"],
            flags=row["flags"],
        )

    return cards


def _load_tags(conn: sqlite3.Connection) -> list[Tag]:
    """Load all unique tags."""
    try:
        rows = conn.execute("SELECT tag FROM tags ORDER BY tag").fetchall()
        return [Tag(name=row["tag"]) for row in rows]
    except sqlite3.OperationalError:
        return []


def load_collection(conn: sqlite3.Connection, media_map: dict[str, str]) -> AnkiCollection:
    """Read all tables and build AnkiCollection."""
    notetypes = _load_notetypes(conn)
    decks = _load_decks(conn)
    notes = _load_notes(conn, notetypes)
    cards = _load_cards(conn)
    tags = _load_tags(conn)

    return AnkiCollection(
        notetypes=notetypes,
        decks=decks,
        notes=notes,
        cards=cards,
        tags=tags,
        media_map=media_map,
    )
