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


import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — override via environment variables
# ---------------------------------------------------------------------------



# Sentence Transformers model identifier (HuggingFace Hub or local path)
ST_MODEL_NAME: str = os.getenv("ST_MODEL_NAME", "all-MiniLM-L6-v2")

# Maximum characters fed to the encoder — avoids exceeding the model's 512-token
# context window while keeping the most informative (top) content.
MAX_ENCODE_CHARS: int = int(os.getenv("ST_MAX_CHARS", "4000"))




# ---------------------------------------------------------------------------
# Model & ChromaDB singletons — instantiated once per process
# ---------------------------------------------------------------------------







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
    

    # ── 3. Embed the job description ──────────────────────────────────────────
    logger.debug("Embedding job description (%d chars).", len(job_description))
    jd_vec = _embed(job_description)

    # ── 4. Compute cosine similarity ─────────────────────────────────────────
    similarity = _cosine_similarity(resume_vec, jd_vec)
    logger.info("Cosine similarity for resume '%s': %.4f", resume_id, similarity)

    # ── 5. (Optional) similarity search — top-K nearest resumes to this JD ───
    

    return VectorMatchResult(
        similarity_score = similarity,
        resume_chroma_id = resume_id,
        resume_embedding = resume_vec,
        jd_embedding     = jd_vec,
        top_similar = [],
        model_used       = ST_MODEL_NAME,
    )


# ---------------------------------------------------------------------------
# Utility — delete a resume's vector (call on resume deletion in the DB)
# ---------------------------------------------------------------------------

