#!/usr/bin/env python3
"""
Pre-compute embeddings for all Anki notes.
Run locally on GPU: python scripts/precompute_embeddings.py

Outputs: scripts/output/embeddings.jsonl
Each line: {"note_id": ..., "text": ..., "tags": [...], "notetype": ..., "embedding": [...]}
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running from repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "anki_parser" / "src"))

from anki_parser import parse_apkg
from anki_parser.text import extract_clean_text, is_meaningful_field

APKG_PATH = Path(__file__).parent.parent / "anking" / "AnKing Step Deck.apkg"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "embeddings.jsonl"

# Max characters to feed into embedding model (~450 tokens at ~4 chars/token)
# BioLORD-2023 supports 512 tokens, keep ~88% safety margin
MAX_CHARS = 1800


def prepare_note_text(note, notetype_name: str) -> str:
    """Build the text string to embed for a note."""
    if "AnKingOverhaul" in notetype_name:
        text = note.get_clean_field("Text")
        extra = note.get_clean_field("Extra")
        combined = f"{text} {extra}".strip()
    elif "IO" in notetype_name or "Image" in notetype_name:
        header = note.get_clean_field("Header")
        extra = note.get_clean_field("Extra")
        combined = f"{header} {extra}".strip()
    else:
        # Generic: combine all meaningful fields
        parts = [
            note.get_clean_field(f)
            for f in note.field_values
            if is_meaningful_field(note.get_field(f))
        ]
        combined = " ".join(parts).strip()

    # Add flattened tags as context (limit to avoid overwhelming)
    tag_text = " ".join(
        t.replace("#", "").replace("::", " ")
        for t in note.tags[:5]
    )
    if tag_text:
        combined = f"{combined} [{tag_text}]"

    return combined[:MAX_CHARS]


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-compute Anki note embeddings")
    parser.add_argument("--apkg", default=str(APKG_PATH), help="Path to .apkg file")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Output JSONL path")
    parser.add_argument("--batch-size", type=int, default=256, help="Embedding batch size")
    parser.add_argument("--device", default="cuda", help="Device: cuda or cpu")
    parser.add_argument("--sample", type=int, default=0, help="Process only N notes (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and prepare but don't embed")
    args = parser.parse_args()

    apkg_path = Path(args.apkg)
    output_path = Path(args.output)

    if not apkg_path.exists():
        print(f"ERROR: Anki deck not found: {apkg_path}", file=sys.stderr)
        sys.exit(1)

    # Parse the deck
    print(f"Parsing {apkg_path} ...")
    t0 = time.time()
    collection = parse_apkg(apkg_path)
    print(f"  Parsed {len(collection.notes):,} notes, {len(collection.cards):,} cards "
          f"in {time.time() - t0:.1f}s")

    # Build notetype name lookup
    nt_names = {nt_id: nt.name for nt_id, nt in collection.notetypes.items()}

    # Prepare texts
    print("Preparing note texts ...")
    records = []
    skipped = 0

    notes_list = list(collection.notes.values())
    if args.sample:
        notes_list = notes_list[: args.sample]

    for note in notes_list:
        notetype_name = nt_names.get(note.notetype_id, "")
        text = prepare_note_text(note, notetype_name)
        if not text.strip():
            skipped += 1
            continue
        records.append({
            "note_id": note.id,
            "text": text,
            "tags": note.tags,
            "notetype": notetype_name,
        })

    print(f"  Prepared {len(records):,} records, skipped {skipped} empty notes")

    if args.dry_run:
        print("Dry run — skipping embedding and output.")
        # Print a sample
        for r in records[:3]:
            print(f"  [{r['note_id']}] {r['text'][:120]!r}")
        return

    # Generate embeddings
    print(f"Loading sentence-transformers model on {args.device} ...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("FremyCompany/BioLORD-2023", device=args.device)

    texts = [r["text"] for r in records]
    print(f"Encoding {len(texts):,} texts (batch_size={args.batch_size}) ...")
    t1 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    elapsed = time.time() - t1
    print(f"  Encoded in {elapsed:.1f}s ({len(texts)/elapsed:.0f} notes/sec)")

    # Verify normalization
    import numpy as np
    norms = np.linalg.norm(embeddings, axis=1)
    print(f"  Embedding norms: min={norms.min():.4f}, max={norms.max():.4f} (should be ≈1.0)")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {len(records):,} records to {output_path} ...")
    with open(output_path, "w", encoding="utf-8") as f:
        for record, emb in zip(records, embeddings):
            line = {
                "note_id": record["note_id"],
                "text": record["text"],
                "tags": record["tags"],
                "notetype": record["notetype"],
                "embedding": emb.tolist(),
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Done. Output: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
