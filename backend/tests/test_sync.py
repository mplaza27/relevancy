"""Tests for the sync API script generation."""

from app.api.sync import SCRIPT_TEMPLATE


class TestScriptTemplate:
    def test_template_renders_with_note_ids(self):
        note_ids = [123456, 789012, 345678]
        script = SCRIPT_TEMPLATE.format(
            timestamp="2025-01-01 00:00 UTC",
            threshold=0.35,
            note_count=len(note_ids),
            deck_name="AnKing Step Deck",
            note_ids=repr(note_ids),
        )
        # Verify key content is present
        assert "AnKing Step Deck" in script
        assert "2055492159" in script  # AnkiConnect add-on code
        assert str(note_ids) in script
        assert "urllib.request" in script
        assert "def main()" in script

    def test_template_contains_correct_syntax(self):
        """Script should use nid: comma-separated format."""
        note_ids = [111, 222, 333]
        script = SCRIPT_TEMPLATE.format(
            timestamp="2025-01-01 00:00 UTC",
            threshold=0.3,
            note_count=len(note_ids),
            deck_name="AnKing Step Deck",
            note_ids=repr(note_ids),
        )
        assert 'nid:" + ",".join(str(n) for n in batch)' in script

    def test_template_has_suspend_and_unsuspend(self):
        note_ids = [111, 222]
        script = SCRIPT_TEMPLATE.format(
            timestamp="2025-01-01 00:00 UTC",
            threshold=0.3,
            note_count=len(note_ids),
            deck_name="AnKing Step Deck",
            note_ids=repr(note_ids),
        )
        assert '"suspend"' in script
        assert '"unsuspend"' in script

    def test_template_no_import_issues(self):
        """Script uses only stdlib — no external imports."""
        note_ids = [1]
        script = SCRIPT_TEMPLATE.format(
            timestamp="2025-01-01 00:00 UTC",
            threshold=0.3,
            note_count=len(note_ids),
            deck_name="AnKing Step Deck",
            note_ids=repr(note_ids),
        )
        # Should only import stdlib
        import_lines = [line for line in script.splitlines() if line.startswith("import ")]
        allowed = {"import json", "import sys", "import urllib.request", "import urllib.error"}
        for line in import_lines:
            assert line in allowed, f"Unexpected import: {line!r}"

    def test_empty_note_ids_still_renders(self):
        """Edge case: no notes above threshold."""
        script = SCRIPT_TEMPLATE.format(
            timestamp="2025-01-01 00:00 UTC",
            threshold=0.99,
            note_count=0,
            deck_name="AnKing Step Deck",
            note_ids=repr([]),
        )
        assert "NOTE_IDS = []" in script
