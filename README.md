# relevancy

A system that takes learning resources (PPTs, videos/transcripts, or syllabi) as input and retrieves the most relevant flashcards from a database to aid studying.

## How It Works

1. **Input Processing**: Extracts text from various resource formats
2. **Embedding Generation**: Converts content into vector representations
3. **Similarity Search**: Finds semantically similar flashcards in the database
4. **Results**: Returns ranked flashcards relevant to the input material

## Possible Tech Stacks

### Option 1: Python-First Stack
- **Text Extraction**: `python-pptx`, `pymupdf`, `whisper` (for transcripts)
- **Embeddings**: `sentence-transformers` or OpenAI embeddings
- **Vector DB**: ChromaDB, Pinecone, or Weaviate
- **API**: FastAPI with `uvicorn`
- **CLI**: `typer` or `click`

### Option 2: Lightweight Stack
- **Embeddings**: Ollama with local models (e.g., `nomic-embed-text`)
- **Vector DB**: ChromaDB (in-memory or persistent)
- **Framework**: `chainlit` or simple `argparse` CLI

### Option 3: Cloud-Native Stack
- **Embeddings**: AWS Bedrock, Google Vertex AI, or OpenAI API
- **Vector DB**: Pinecone, Weaviate Cloud, or Supabase pgvector
- **Deployment**: Docker + AWS Lambda or Google Cloud Run

## Implementation Approaches

### Phase 1: Core Pipeline
1. Build text extractors for PPT (`.pptx`), PDF (`.pdf`), and plain text (`.txt`, `.md`)
2. Implement embedding generation with a local model
3. Set up vector DB with initial flashcard collection
4. Create similarity search endpoint

### Phase 2: Enhancements
- Add video transcript support via Whisper or assemblyAI
- Support for syllabus parsing (structured text extraction)
- Re-ranking with cross-encoders for better relevance
- Caching layer for frequently queried resources

### Phase 3: Polish
- CLI interface for batch processing
- Web UI for interactive search
- Flashcard import/export (Anki, Quizlet formats)
- User feedback loop to improve retrieval

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run the CLI
python main.py --input lecture.pdf
```
