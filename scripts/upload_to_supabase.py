#!/usr/bin/env python3
"""
Upload pre-computed embeddings to Supabase.

Usage:
    DATABASE_URL="postgresql://..." python scripts/upload_to_supabase.py

Reads: scripts/output/embeddings.jsonl
Inserts into: anki_notes table
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


INPUT_FILE = Path(__file__).parent / "output" / "embeddings.jsonl"
BATCH_SIZE = 500  # rows per INSERT batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload embeddings to Supabase")
    parser.add_argument("--input", default=str(INPUT_FILE), help="Input JSONL path")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Insert batch size")
    parser.add_argument("--truncate", action="store_true", help="Truncate table before inserting")
    parser.add_argument("--dry-run", action="store_true", help="Parse input without inserting")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL environment variable not set", file=sys.stderr)
        print("  Use direct connection (port 5432), not pooler (port 6543)", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read all records
    print(f"Reading {input_path} ...")
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"  Read {len(records):,} records")

    if args.dry_run:
        print("Dry run — skipping database upload.")
        for r in records[:3]:
            print(f"  [{r['note_id']}] {r['text'][:80]!r}  emb_len={len(r['embedding'])}")
        return

    # Connect to Supabase
    import psycopg
    from pgvector.psycopg import register_vector

    print(f"Connecting to database ...")
    with psycopg.connect(db_url) as conn:
        register_vector(conn)

        if args.truncate:
            print("Truncating anki_notes table ...")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE anki_notes CASCADE")
            conn.commit()

        print(f"Inserting {len(records):,} records in batches of {args.batch_size} ...")
        t0 = time.time()
        total_inserted = 0

        with conn.cursor() as cur:
            for i in range(0, len(records), args.batch_size):
                batch = records[i : i + args.batch_size]

                cur.executemany(
                    """
                    INSERT INTO anki_notes (note_id, notetype, text, tags, embedding, textsearch)
                    VALUES (%s, %s, %s, %s, %s, to_tsvector('english', %s))
                    ON CONFLICT (note_id) DO UPDATE
                      SET notetype = EXCLUDED.notetype,
                          text = EXCLUDED.text,
                          tags = EXCLUDED.tags,
                          embedding = EXCLUDED.embedding,
                          textsearch = EXCLUDED.textsearch
                    """,
                    [
                        (
                            r["note_id"],
                            r["notetype"],
                            r["text"],
                            r["tags"],
                            r["embedding"],
                            r["text"],
                        )
                        for r in batch
                    ],
                )
                conn.commit()
                total_inserted += len(batch)

                elapsed = time.time() - t0
                rate = total_inserted / elapsed if elapsed > 0 else 0
                print(f"  {total_inserted:,}/{len(records):,} ({rate:.0f} rows/sec)", end="\r")

        elapsed = time.time() - t0
        print(f"\nDone. Inserted {total_inserted:,} rows in {elapsed:.1f}s "
              f"({total_inserted/elapsed:.0f} rows/sec)")


if __name__ == "__main__":
    main()
