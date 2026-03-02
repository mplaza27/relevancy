#!/usr/bin/env python3
"""Suite 5 — Sync Script Dry Run.

Renders the sync script template with test note IDs, enables DRY_RUN mode,
and executes the script to verify it runs correctly without a live Anki instance.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parents[2]))

from app.api.sync import SCRIPT_TEMPLATE  # noqa: E402

TEST_NOTE_IDS = [111111111, 222222222, 333333333]

script = SCRIPT_TEMPLATE.format(
    timestamp="2025-01-01 00:00 UTC",
    threshold=0.3,
    note_count=len(TEST_NOTE_IDS),
    deck_name="AnKing Step Deck",
    note_ids=repr(TEST_NOTE_IDS),
)

# Enable dry-run mode so the script never touches AnkiConnect
script = script.replace("DRY_RUN = False", "DRY_RUN = True")
assert "DRY_RUN = True" in script, "DRY_RUN flag not present in rendered script"

with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
    f.write(script)
    tmp_path = Path(f.name)

try:
    result = subprocess.run(
        [sys.executable, str(tmp_path)],
        capture_output=True,
        text=True,
    )
finally:
    tmp_path.unlink(missing_ok=True)

print(result.stdout)
if result.stderr:
    print(f"STDERR: {result.stderr}", file=sys.stderr)

if result.returncode != 0:
    print(f"FAIL: script exited with code {result.returncode}", file=sys.stderr)
    sys.exit(1)

# Verify expected output markers
checks = [
    ("[DRY RUN]", "DRY RUN actions not printed"),
    ("Connected", "AnkiConnect version check not printed"),
    ("SYNC COMPLETE", "Sync completion message missing"),
    ("UNSUSPENDED", "Unsuspend summary missing"),
]
for marker, msg in checks:
    if marker not in result.stdout:
        print(f"FAIL: {msg} (expected '{marker}' in output)", file=sys.stderr)
        sys.exit(1)

print("Suite 5 — Sync Script Dry Run: PASS")
