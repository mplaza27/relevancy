[x]
# Prompt 06: Document Parsing Service

## Goal
Implement text extraction from uploaded documents (PDF, PPTX, DOCX, TXT, MD) and a text chunking strategy suitable for the 256-token limit of `all-MiniLM-L6-v2`.

## Context
- Location: `backend/app/services/document_parser.py` and `backend/app/services/chunker.py`
- PDF extraction: `pymupdf4llm` (wrapper around PyMuPDF, outputs Markdown with table preservation)
- PPTX extraction: `python-pptx`
- DOCX extraction: `python-docx`
- Chunk target: ~200 tokens (~800 chars) with ~50 token overlap
- Medical PDFs may have images, tables, multi-column layouts

## Files to Implement

### 1. `backend/app/services/document_parser.py` — Text extraction

**PDF** — Use `pymupdf4llm.to_markdown()`:
```python
import pymupdf4llm

def extract_pdf(file_path: Path) -> str:
    return pymupdf4llm.to_markdown(str(file_path))
```
This handles tables (GitHub-flavored Markdown), multi-column layouts, and embedded text. For OCR on scanned pages, PyMuPDF has built-in OCR support if `tesseract` is available, but don't require it.

**PPTX** — Use `python-pptx`:
- Iterate slides → shapes
- Extract text from `shape.text_frame.paragraphs`
- Extract text from `shape.table` rows/cells
- Prefix each slide: `## Slide N`
- Join with double newlines

**DOCX** — Use `python-docx`:
- Iterate `doc.element.body` children in order
- Extract paragraph text
- Extract table text (row cells joined by ` | `)

**TXT/MD** — Read as UTF-8 text directly.

**Router function:**
```python
def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    extractors = {
        ".pdf": extract_pdf,
        ".pptx": extract_pptx,
        ".docx": extract_docx,
        ".txt": lambda p: p.read_text(encoding="utf-8"),
        ".md": lambda p: p.read_text(encoding="utf-8"),
    }
    extractor = extractors.get(suffix)
    if not extractor:
        raise ValueError(f"Unsupported file type: {suffix}")
    return extractor(file_path)
```

### 2. `backend/app/services/chunker.py` — Text chunking

**Key constraint:** `all-MiniLM-L6-v2` has max_seq_length of **256 tokens** (not 512). Chunks must be ~200 tokens to leave headroom.

**Strategy: Sentence-boundary aware sliding window**
```python
def chunk_text(
    text: str,
    max_tokens: int = 200,
    overlap_tokens: int = 50,
    chars_per_token: float = 4.0,
) -> list[str]:
```

Algorithm:
1. Split text into sentences (regex: `r'(?<=[.!?])\s+'`)
2. Accumulate sentences into a chunk until `max_chars` is exceeded
3. Emit the chunk
4. Carry forward the last few sentences as overlap (up to `overlap_chars`)
5. Continue until all sentences are consumed
6. Don't forget the final chunk

**Edge cases:**
- Very long sentences (>max_chars): split at word boundaries
- Empty text: return empty list
- Text shorter than one chunk: return as single chunk
- Tables in Markdown: try to keep table rows together

**Return type:** `list[str]` — each string is a chunk ready for embedding.

## Testing

### `backend/tests/test_document_parser.py`
- Test PDF extraction with a small test PDF (create a fixture or mock)
- Test PPTX extraction
- Test DOCX extraction
- Test unsupported extension raises ValueError

### `backend/tests/test_chunker.py`
- Test short text returns single chunk
- Test long text splits into multiple chunks
- Test overlap is present between consecutive chunks
- Test empty text returns empty list
- Test chunks are all under max_chars limit
- Test with real-world medical text sample

## Verification
```python
from app.services.document_parser import extract_text
from app.services.chunker import chunk_text

text = extract_text(Path("test_lecture.pdf"))
chunks = chunk_text(text)
print(f"Extracted {len(text)} chars, split into {len(chunks)} chunks")
for i, chunk in enumerate(chunks[:3]):
    print(f"  Chunk {i}: {len(chunk)} chars, ~{len(chunk)//4} tokens")
    print(f"    Preview: {chunk[:100]}...")
```
