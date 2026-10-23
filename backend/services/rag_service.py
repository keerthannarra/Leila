"""
rag_service.py — RAG pipeline for Leila IT Help Desk Agent.

Uses a hybrid BM25-style keyword scoring so short queries match long articles
without needing compiled ML libraries. Embeddings are stored but not used for
scoring in demo mode; swap `_keyword_score` for `cosine_similarity` when a
real embeddings API is configured.
"""
from __future__ import annotations

import json
import math
import re
from typing import List, Tuple

from sqlalchemy.orm import Session as DBSession

from models import ArticleChunk, DocumentChunk
from services.groq_service import get_embedding  # kept for chunk storage

_STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "do",
    "i", "my", "me", "we", "you", "your", "of", "for", "and", "or",
    "not", "but", "this", "that", "with", "have", "has", "had",
    "be", "was", "are", "were", "can", "will", "how", "what", "when",
    "where", "why", "does", "did", "please", "help", "need", "get",
    "just", "so", "if", "about", "from", "by", "use", "any", "also",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumeric, remove stop words, apply minimal stemming."""
    raw = re.split(r"[^a-z0-9]+", text.lower())
    tokens = []
    for w in raw:
        if not w or w in _STOP_WORDS:
            continue
        # Minimal suffix stripping for common English inflections
        if len(w) > 5 and w.endswith("ing"):
            w = w[:-3]       # turning → turn, connecting → connect
        elif len(w) > 4 and w.endswith("ed"):
            w = w[:-2]       # connected → connect
        elif len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]       # steps → step (but not "class" → "clas")
        tokens.append(w)
    return tokens


def _keyword_score(query: str, chunk_text: str) -> float:
    """
    BM25-inspired keyword overlap score.

    - Query tokens that appear in the chunk contribute positively.
    - Longer chunks are penalised slightly (length normalisation).
    - Score is clamped to [0, 1] and maps naturally to our confidence bands.
    """
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0

    c_tokens = _tokenize(chunk_text)
    c_token_set = set(c_tokens)
    c_len = max(len(c_tokens), 1)

    # BM25 parameters
    k1 = 1.5
    b = 0.75
    avg_doc_len = 120  # approximate average chunk length in tokens

    score = 0.0
    for qt in q_tokens:
        # Term frequency in chunk
        tf = c_tokens.count(qt)
        if tf == 0:
            # Try prefix match (handles "won't" → "wont" vs "wont" in chunk)
            tf = sum(1 for ct in c_tokens if ct.startswith(qt) or qt.startswith(ct))
        if tf == 0:
            continue
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * c_len / avg_doc_len))
        # IDF weight: rare tokens (short query, many doc tokens) → higher weight
        idf = math.log(1 + (avg_doc_len / (1 + tf)))
        score += idf * tf_norm

    # Normalise: divide by max possible score (all query tokens present at tf=3)
    max_tf_norm = (3 * (k1 + 1)) / (3 + k1)
    max_idf = math.log(1 + avg_doc_len)
    max_score = len(q_tokens) * max_idf * max_tf_norm
    normalised = score / max_score if max_score > 0 else 0.0

    return min(normalised, 1.0)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two float vectors (used when real embeddings are available)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_confidence_band(score: float) -> str:
    """Map a similarity score to a confidence band string."""
    if score >= 0.50:
        return "HIGH"
    if score >= 0.30:
        return "LOW"
    return "NONE"


def retrieve_chunks(
    query: str,
    db: DBSession,
    top_k: int = 5,
) -> List[dict]:
    """
    Score all approved chunks against the query using keyword overlap.
    Returns top_k results sorted by score descending.
    """
    results: List[dict] = []

    for chunk in db.query(ArticleChunk).filter(ArticleChunk.approved_status == True).all():
        score = _keyword_score(query, chunk.chunk_text)
        results.append({
            "chunk_text": chunk.chunk_text,
            "article_id": chunk.article_id,
            "chunk_id": chunk.id,
            "source_type": "article",
            "similarity_score": score,
        })

    for chunk in db.query(DocumentChunk).filter(DocumentChunk.approved_status == True).all():
        score = _keyword_score(query, chunk.chunk_text)
        results.append({
            "chunk_text": chunk.chunk_text,
            "article_id": chunk.document_id,
            "chunk_id": chunk.id,
            "source_type": "document",
            "similarity_score": score,
        })

    results.sort(key=lambda r: r["similarity_score"], reverse=True)
    return results[:top_k]


def search_knowledge_base(
    query: str,
    db: DBSession,
    top_k: int = 5,
) -> Tuple[List[dict], float, str]:
    """
    Full RAG pipeline: keyword score all chunks, return top_k with band.
    Returns: (chunks, best_score, confidence_band)
    """
    chunks = retrieve_chunks(query, db, top_k=top_k)

    if not chunks:
        return [], 0.0, "NONE"

    best_score = chunks[0]["similarity_score"]
    band = get_confidence_band(best_score)
    return chunks, best_score, band
