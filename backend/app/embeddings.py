from __future__ import annotations

import numpy as np

_model = None


def load_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load the sentence-transformers model. Call once at startup."""
    from sentence_transformers import SentenceTransformer

    global _model
    _model = SentenceTransformer(model_name)
    return _model


def is_loaded() -> bool:
    """Return True if the model has been loaded."""
    return _model is not None


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Embed multiple texts. Returns (n, 384) float32 array, L2-normalized.

    Call via asyncio.to_thread() in async handlers — this is CPU-bound.
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    return _model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )


def embed_query(text: str) -> np.ndarray:
    """Embed a single text. Returns (384,) float32 array, L2-normalized.

    Call via asyncio.to_thread() in async handlers — this is CPU-bound.
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    result = _model.encode(text, normalize_embeddings=True)
    # Ensure 1D array
    return np.asarray(result, dtype=np.float32).flatten()
