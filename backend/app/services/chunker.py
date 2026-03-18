from __future__ import annotations

import re

# Split on sentence-ending punctuation followed by whitespace.
# Preserve the separator to keep sentence structure.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Token estimate: ~4 characters per token for English text
_CHARS_PER_TOKEN = 4.0


def chunk_text(
    text: str,
    max_tokens: int = 400,
    overlap_tokens: int = 80,
    chars_per_token: float = _CHARS_PER_TOKEN,
) -> list[str]:
    """Split text into overlapping chunks suitable for embedding.

    Uses sentence-boundary awareness to avoid splitting mid-sentence.
    Each chunk is approximately max_tokens tokens (bounded by max_chars).

    Parameters:
        text: Input text to chunk.
        max_tokens: Target maximum tokens per chunk (~400 for 512-token limit).
        overlap_tokens: Overlap between consecutive chunks in tokens.
        chars_per_token: Characters per token estimate.

    Returns:
        List of text chunks, each within the token limit.
    """
    text = text.strip()
    if not text:
        return []

    max_chars = int(max_tokens * chars_per_token)
    overlap_chars = int(overlap_tokens * chars_per_token)

    # Split into sentences
    sentences = _SENTENCE_RE.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        # Handle oversized sentences by splitting at word boundaries
        if len(sentence) > max_chars:
            # Flush current chunk first
            if current:
                chunks.append(" ".join(current))
                # Carry overlap
                current, current_len = _carry_overlap(current, overlap_chars)

            # Split oversized sentence into word-boundary sub-chunks
            sub_chunks = _split_long_sentence(sentence, max_chars, overlap_chars)
            # All but last go directly to output
            for sub in sub_chunks[:-1]:
                chunks.append(sub)
            # Last sub-chunk seeds the next accumulation
            if sub_chunks:
                last_sub = sub_chunks[-1]
                current = [last_sub]
                current_len = len(last_sub)
            continue

        if current_len + len(sentence) + 1 > max_chars and current:
            # Emit current chunk
            chunks.append(" ".join(current))
            # Carry overlap sentences forward
            current, current_len = _carry_overlap(current, overlap_chars)

        current.append(sentence)
        current_len += len(sentence) + 1  # +1 for space

    # Emit the final chunk
    if current:
        final = " ".join(current)
        if final not in (chunks[-1] if chunks else ""):
            chunks.append(final)

    return chunks


def _carry_overlap(sentences: list[str], overlap_chars: int) -> tuple[list[str], int]:
    """Return the tail of sentences that fits within overlap_chars."""
    carried: list[str] = []
    length = 0
    for s in reversed(sentences):
        if length + len(s) + 1 > overlap_chars:
            break
        carried.insert(0, s)
        length += len(s) + 1
    return carried, length


def _split_long_sentence(sentence: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split a single oversized sentence at word boundaries."""
    words = sentence.split()
    chunks: list[str] = []
    current_words: list[str] = []
    current_len = 0

    for word in words:
        if current_len + len(word) + 1 > max_chars and current_words:
            chunks.append(" ".join(current_words))
            # Overlap: carry back some words
            overlap_words: list[str] = []
            ol = 0
            for w in reversed(current_words):
                if ol + len(w) + 1 > overlap_chars:
                    break
                overlap_words.insert(0, w)
                ol += len(w) + 1
            current_words = overlap_words
            current_len = ol

        current_words.append(word)
        current_len += len(word) + 1

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
