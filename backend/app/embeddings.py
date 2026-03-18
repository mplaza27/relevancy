from __future__ import annotations

import numpy as np

_bi_encoder = None
_cross_encoder = None


def load_model(model_name: str = "FremyCompany/BioLORD-2023"):
    """Load the sentence-transformers bi-encoder model. Call once at startup."""
    from sentence_transformers import SentenceTransformer

    global _bi_encoder
    _bi_encoder = SentenceTransformer(model_name)
    return _bi_encoder


def is_loaded() -> bool:
    """Return True if the bi-encoder model has been loaded."""
    return _bi_encoder is not None


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Embed multiple texts. Returns (n, 768) float32 array, L2-normalized.

    Call via asyncio.to_thread() in async handlers — this is CPU-bound.
    """
    if _bi_encoder is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    return _bi_encoder.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )


def embed_query(text: str) -> np.ndarray:
    """Embed a single text. Returns (768,) float32 array, L2-normalized.

    Call via asyncio.to_thread() in async handlers — this is CPU-bound.
    """
    if _bi_encoder is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() first.")
    result = _bi_encoder.encode(text, normalize_embeddings=True)
    # Ensure 1D array
    return np.asarray(result, dtype=np.float32).flatten()


# --- Cross-encoder support ---


def load_cross_encoder(model_name: str = "ncbi/MedCPT-Cross-Encoder"):
    """Load the cross-encoder reranker model. Call once at startup."""
    from sentence_transformers import CrossEncoder

    global _cross_encoder
    _cross_encoder = CrossEncoder(model_name)
    return _cross_encoder


def is_cross_encoder_loaded() -> bool:
    """Return True if the cross-encoder model has been loaded."""
    return _cross_encoder is not None


def cross_encode(pairs: list[tuple[str, str]], batch_size: int = 64) -> np.ndarray:
    """Score query-document pairs with cross-encoder.

    Returns 1D float32 array of logits (one per pair).
    Call via asyncio.to_thread() — this is CPU-bound.
    """
    if _cross_encoder is None:
        raise RuntimeError("Cross-encoder not loaded. Call load_cross_encoder() first.")
    scores = _cross_encoder.predict(pairs, batch_size=batch_size, show_progress_bar=False)
    return np.asarray(scores, dtype=np.float32).flatten()
