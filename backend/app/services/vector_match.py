"""
services/vector_match.py — Semantic similarity via Sentence Transformers + ChromaDB.

Pipeline (called by main.py):
  1. Load / cache the SentenceTransformer model (all-MiniLM-L6-v2)
  2. Embed the resume text into a 384-dim dense vector
  3. Upsert the vector into ChromaDB (keyed by resume_id)
  4. Embed the job-description text
  5. Compute cosine similarity between resume & JD vectors
  6. Optionally query ChromaDB to find the top-N most similar stored resumes
     (useful for recruiter-side "find matching candidates" feature)
  7. Return a VectorMatchResult dataclass

Dependencies (add to requirements.txt):
    sentence-transformers>=3.0.0
    chromadb>=0.5.0
    numpy>=1.26.0
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import numpy as np
from chromadb import Client, Collection, EphemeralClient, PersistentClient
from chromadb.config import Settings

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — override via environment variables
# ---------------------------------------------------------------------------

# Where ChromaDB persists its on-disk index (use a volume mount in Docker)
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Collection name inside ChromaDB that holds resume vectors
CHROMA_COLLECTION:  str = os.getenv("CHROMA_COLLECTION", "resumes")

# Sentence Transformers model identifier (HuggingFace Hub or local path)
ST_MODEL_NAME: str = os.getenv("ST_MODEL_NAME", "all-MiniLM-L6-v2")

# Maximum characters fed to the encoder — avoids exceeding the model's 512-token
# context window while keeping the most informative (top) content.
MAX_ENCODE_CHARS: int = int(os.getenv("ST_MAX_CHARS", "4000"))

# Number of nearest neighbours returned by similarity_search()
DEFAULT_TOP_K: int = 5


# ---------------------------------------------------------------------------
# Model & ChromaDB singletons — instantiated once per process
# ---------------------------------------------------------------------------




def _get_chroma_client() -> Client:
    """Return a persistent ChromaDB client, creating the directory if needed."""
    return PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def _get_collection() -> Collection:
    """Return (or create) the resume vectors collection in ChromaDB.

    ``get_or_create_collection`` is idempotent — safe to call on every request.
    The ``cosine`` distance metric aligns with our similarity scoring approach.
    """
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},   # use cosine distance for HNSW index
    )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class VectorMatchResult:
    """Output contract returned to the API layer.

    Attributes:
        similarity_score:  Cosine similarity ∈ [0, 1] between resume & JD.
        resume_chroma_id:  The ChromaDB document ID under which the resume
                           vector is now stored (stable across re-embeds).
        resume_embedding:  Raw 384-dim numpy array (useful for debugging).
        jd_embedding:      Raw 384-dim numpy array for the job description.
        top_similar:       (Optional) Top-K resumes nearest to the JD —
                           populated when ``run_similarity_search=True``.
        model_used:        Name of the Sentence Transformers model.
    """

    similarity_score:  float
    resume_chroma_id:  str
    resume_embedding:  np.ndarray
    jd_embedding:      np.ndarray
    top_similar:       list[dict]    = field(default_factory=list)
    model_used:        str           = ST_MODEL_NAME


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _embed(text: str) -> np.ndarray:
    text = text[:MAX_ENCODE_CHARS]

    response = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )

    vector = np.array(response["embedding"], dtype=np.float32)

    # normalize
    vector = vector / np.linalg.norm(vector)

    return vector


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two L2-normalised vectors.

    Since both vectors are already unit-norm (from ``normalize_embeddings``),
    cosine similarity reduces to a simple dot product — fast and numerically
    stable.

    Returns:
        A float in [-1, 1]; clipped to [0, 1] for interpretability.
    """
    score = float(np.dot(a, b))
    return max(0.0, min(1.0, score))   # guard against tiny floating-point drift


# ---------------------------------------------------------------------------
# ChromaDB upsert / query
# ---------------------------------------------------------------------------

def _upsert_resume_vector(
    resume_id:  str,
    embedding:  np.ndarray,
    metadata:   Optional[dict] = None,
) -> str:
    """Upsert a resume's embedding into ChromaDB.

    Using ``upsert`` (not ``add``) is idempotent — re-running the pipeline
    for the same resume simply refreshes the vector without duplicating it.

    Args:
        resume_id:  Stable identifier, typically the DB UUID as a string.
        embedding:  Float32 array from ``_embed()``.
        metadata:   Optional key-value pairs stored alongside the vector
                    (e.g. owner_id, filename, parsed skills list).

    Returns:
        The ChromaDB document ID (== resume_id).
    """
    collection = _get_collection()
    collection.upsert(
        ids=[resume_id],
        embeddings=[embedding.tolist()],   # ChromaDB expects a plain Python list
        metadatas=[metadata or {}],
    )
    logger.debug("Upserted resume vector '%s' into ChromaDB.", resume_id)
    return resume_id


def _query_similar_resumes(
    jd_embedding: np.ndarray,
    top_k:        int = DEFAULT_TOP_K,
    where:        Optional[dict] = None,
) -> list[dict]:
    """Query ChromaDB for the top-K resumes closest to *jd_embedding*.

    Args:
        jd_embedding:  Normalised embedding of the job description.
        top_k:         Number of results to return.
        where:         Optional ChromaDB metadata filter
                       (e.g. ``{"owner_id": {"$eq": "abc123"}}``).

    Returns:
        A list of dicts, each containing ``id``, ``distance``, and ``metadata``.
    """
    collection = _get_collection()
    n_docs = collection.count()
    if n_docs == 0:
        logger.warning("ChromaDB collection is empty — no similar resumes found.")
        return []

    effective_k = min(top_k, n_docs)
    query_kwargs: dict = dict(
        query_embeddings=[jd_embedding.tolist()],
        n_results=effective_k,
        include=["distances", "metadatas"],
    )
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    # Unpack the nested ChromaDB result structure into a flat list
    hits: list[dict] = []
    ids       = results.get("ids",       [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for doc_id, dist, meta in zip(ids, distances, metadatas):
        # ChromaDB returns squared L2 or cosine distance; convert to similarity
        similarity = max(0.0, 1.0 - float(dist))
        hits.append({"id": doc_id, "similarity": similarity, "metadata": meta})

    return hits


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def embed_and_match(
    resume_text:         str,
    job_description:     str,
    resume_id:           str,
    resume_metadata:     Optional[dict] = None,
    run_similarity_search: bool         = False,
    top_k:               int            = DEFAULT_TOP_K,
) -> VectorMatchResult:
    """Embed a resume, store it in ChromaDB, and score it against a JD.

    This is the single entry-point called from ``main.py``.

    Args:
        resume_text:           Cleaned text from ``parser.ParseResult.cleaned_text``.
        job_description:       Raw job-description text submitted by the user.
        resume_id:             Stable ID (UUID string) used as the ChromaDB key.
        resume_metadata:       Arbitrary dict stored alongside the vector
                               (e.g. owner, filename, top skills).
        run_similarity_search: When True, also query for top-K nearest resumes
                               (useful for the "candidate matching" recruiter flow).
        top_k:                 Number of nearest neighbours to return.

    Returns:
        A :class:`VectorMatchResult` with scores and optional neighbour list.

    Raises:
        ValueError: If either text argument is empty after stripping.
    """
    if not resume_text.strip():
        raise ValueError("resume_text must not be empty.")
    if not job_description.strip():
        raise ValueError("job_description must not be empty.")

    # ── 1. Embed the resume ───────────────────────────────────────────────────
    # NOTE: In production, wrap both encode calls with asyncio.to_thread()
    # to avoid blocking the event loop on CPU-bound inference.
    logger.debug("Embedding resume '%s' (%d chars).", resume_id, len(resume_text))
    resume_vec = _embed(resume_text)

    # ── 2. Persist the resume vector in ChromaDB ─────────────────────────────
    chroma_id = _upsert_resume_vector(
        resume_id=resume_id,
        embedding=resume_vec,
        metadata=resume_metadata or {},
    )

    # ── 3. Embed the job description ──────────────────────────────────────────
    logger.debug("Embedding job description (%d chars).", len(job_description))
    jd_vec = _embed(job_description)

    # ── 4. Compute cosine similarity ─────────────────────────────────────────
    similarity = _cosine_similarity(resume_vec, jd_vec)
    logger.info("Cosine similarity for resume '%s': %.4f", resume_id, similarity)

    # ── 5. (Optional) similarity search — top-K nearest resumes to this JD ───
    top_similar: list[dict] = []
    if run_similarity_search:
        top_similar = _query_similar_resumes(jd_vec, top_k=top_k)
        logger.debug("Top-%d similar resumes retrieved.", len(top_similar))

    return VectorMatchResult(
        similarity_score = similarity,
        resume_chroma_id = chroma_id,
        resume_embedding = resume_vec,
        jd_embedding     = jd_vec,
        top_similar      = top_similar,
        model_used       = ST_MODEL_NAME,
    )


# ---------------------------------------------------------------------------
# Utility — delete a resume's vector (call on resume deletion in the DB)
# ---------------------------------------------------------------------------

def delete_resume_vector(resume_id: str) -> bool:
    """Remove a resume's embedding from ChromaDB.

    Returns True if the document was present and deleted, False otherwise.
    """
    collection = _get_collection()
    try:
        collection.delete(ids=[resume_id])
        logger.info("Deleted ChromaDB vector for resume '%s'.", resume_id)
        return True
    except Exception as exc:
        logger.warning("Could not delete vector '%s': %s", resume_id, exc)
        return False
