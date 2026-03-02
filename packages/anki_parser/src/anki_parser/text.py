from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

# Matches innermost cloze (no nested braces in content): {{cN::content}}
_SIMPLE_CLOZE_RE = re.compile(r"\{\{c\d+::([^{}]*)\}\}")
# Sound reference: [sound:filename.mp3]
_SOUND_REF_RE = re.compile(r"\[sound:[^\]]+\]")
# Sound filename extraction
_SOUND_NAME_RE = re.compile(r"\[sound:([^\]]+)\]")
# Collapse whitespace
_WHITESPACE_RE = re.compile(r"\s+")


def strip_cloze(text: str) -> str:
    """Replace {{cN::answer::hint}} with the answer text. Handles nesting iteratively.

    Processes innermost cloze first (those with no nested braces), repeating
    until no cloze markers remain.
    """

    def _extract_answer(m: re.Match) -> str:
        # Content may be "answer" or "answer::hint" — take part before first "::"
        content = m.group(1)
        return content.split("::", 1)[0]

    prev = None
    while prev != text:
        prev = text
        text = _SIMPLE_CLOZE_RE.sub(_extract_answer, text)
    return text


def strip_sound_refs(text: str) -> str:
    """Remove [sound:filename] patterns."""
    return _SOUND_REF_RE.sub("", text)


def extract_image_refs(html: str) -> list[str]:
    """Return list of image filenames from <img src="..."> tags."""
    if not html:
        return []
    try:
        parser = LexborHTMLParser(html)
        refs = []
        for node in parser.css("img"):
            src = node.attributes.get("src", "")
            if src:
                refs.append(src)
        return refs
    except Exception:
        return []


def extract_sound_refs(html: str) -> list[str]:
    """Return list of sound filenames from [sound:...] patterns."""
    return _SOUND_NAME_RE.findall(html)


def strip_html(html: str) -> str:
    """Convert <br>/<p>/<div> to newlines, strip all tags, collapse whitespace."""
    if not html:
        return ""
    try:
        # Replace block-level tags and <br> with newlines before parsing
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        parser = LexborHTMLParser(text)
        # Add newlines after block elements
        for node in parser.css("p, div, li"):
            # Insert newline by appending to text content
            node.insert_after("\n")
        result = parser.body.text(separator="") if parser.body else ""
    except Exception:
        # Fallback: crude tag stripping
        result = re.sub(r"<[^>]+>", " ", html)

    # Normalize whitespace (preserve paragraph breaks as single newlines)
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in result.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def extract_clean_text(html: str) -> str:
    """Full pipeline: strip_cloze → strip_sound_refs → strip_html → clean."""
    if not html:
        return ""
    text = strip_cloze(html)
    text = strip_sound_refs(text)
    text = strip_html(text)
    return text


def is_meaningful_field(html: str) -> bool:
    """Return False for empty, whitespace-only, or image-only fields."""
    if not html or not html.strip():
        return False
    clean = extract_clean_text(html)
    return bool(clean.strip())
