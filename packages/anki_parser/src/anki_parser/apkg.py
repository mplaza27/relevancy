from __future__ import annotations

import json
import zipfile
from pathlib import Path

import zstandard

from anki_parser.database import load_collection, open_anki_db
from anki_parser.models import AnkiCollection

_ANKI21B = "collection.anki21b"  # zstd-compressed
_ANKI21 = "collection.anki21"  # plain SQLite (newer format)
_ANKI2 = "collection.anki2"  # legacy SQLite


def _decompress_zstd(data: bytes) -> bytes:
    """Decompress a zstd-compressed byte string."""
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data, max_output_size=1024 * 1024 * 1024)  # 1GB max


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read a protobuf varint starting at pos. Returns (value, new_pos)."""
    value = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return value, pos


def _parse_media_protobuf(data: bytes) -> dict[str, str]:
    """Parse the modern Anki media protobuf format.

    The file is a sequence of length-delimited entries (field 1, wire type 2).
    Each entry contains field 1 = filename (string). The entry index (0-based)
    maps to the numeric filename in the ZIP archive.

    Returns: {"0": "filename.webp", "1": "other.png", ...}
    """
    media_map: dict[str, str] = {}
    index = 0
    pos = 0

    while pos < len(data):
        tag = data[pos]
        pos += 1

        wire_type = tag & 0x07
        # field_num = tag >> 3  # field 1 for outer entries

        if wire_type == 2:  # length-delimited
            entry_len, pos = _read_varint(data, pos)
            entry_end = pos + entry_len
            entry_data = data[pos:entry_end]
            pos = entry_end

            # Parse entry to extract field 1 (filename)
            filename = _extract_string_field1(entry_data)
            if filename:
                media_map[str(index)] = filename
            index += 1
        else:
            # Unexpected wire type — stop
            break

    return media_map


def _extract_string_field1(data: bytes) -> str:
    """Extract the first string field (field 1, wire type 2) from protobuf bytes."""
    pos = 0
    while pos < len(data):
        if pos >= len(data):
            break
        tag = data[pos]
        pos += 1
        wire_type = tag & 0x07
        field_num = tag >> 3

        if wire_type == 0:  # varint
            _, pos = _read_varint(data, pos)
        elif wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            value = data[pos : pos + length]
            pos += length
            if field_num == 1:
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    return value.decode("latin-1")
        elif wire_type == 1:  # 64-bit
            pos += 8
        elif wire_type == 5:  # 32-bit
            pos += 4
        else:
            break

    return ""


def _extract_media_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Parse the 'media' file — supports JSON (legacy) and zstd protobuf (modern)."""
    names = zf.namelist()
    if "media" not in names:
        return {}

    try:
        raw = zf.read("media")
        if not raw:
            return {}

        # Detect zstd magic bytes (0x28 0xb5 0x2f 0xfd)
        if raw[:4] == b"\x28\xb5\x2f\xfd":
            decompressed = _decompress_zstd(raw)
            return _parse_media_protobuf(decompressed)

        # Try plain JSON (legacy format)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def parse_apkg(path: str | Path) -> AnkiCollection:
    """Parse an Anki .apkg file and return an AnkiCollection.

    Supports:
    - collection.anki21b (zstd-compressed, modern format)
    - collection.anki21 (plain SQLite, newer)
    - collection.anki2 (plain SQLite, legacy)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Anki package not found: {path}")

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        media_map = _extract_media_map(zf)

        if _ANKI21B in names:
            compressed = zf.read(_ANKI21B)
            db_bytes = _decompress_zstd(compressed)
        elif _ANKI21 in names:
            db_bytes = zf.read(_ANKI21)
        elif _ANKI2 in names:
            db_bytes = zf.read(_ANKI2)
        else:
            raise ValueError(
                f"No recognized Anki collection file found in {path}. "
                f"Available files: {names}"
            )

    with open_anki_db(db_bytes) as conn:
        return load_collection(conn, media_map)
