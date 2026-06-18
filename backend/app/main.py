"""
main.py — FastAPI application entry-point for Smart Resume Analyzer.

Endpoint exposed:
  POST /api/resume/analyze
    • Accepts a multipart-form upload (resume file) + JSON body (job description)
    • Orchestrates: parse → embed → score → LLM feedback → persist
    • Returns a structured AnalysisResponse JSON

Async design notes:
  - CPU-bound work (spaCy NER, Sentence Transformers) is dispatched to a
    thread-pool via asyncio.to_thread() to keep the event loop unblocked.
  - DB sessions use SQLAlchemy's async engine (create_async_engine).
  - All external I/O (DB, ChromaDB writes) is awaited.
"""

from __future__ import annotations
import google.generativeai as genai
import json
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, Optional

import httpx
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import AnalysisHistory, AnalysisStatus, Base, Resume, ResumeStatus
from app.services.parser import ParseResult, parse_resume
#from app.services.vector_match import VectorMatchResult, embed_and_match

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — sourced entirely from environment variables
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:root123@localhost:5432/resume_analyzer",
)
DATABASE_URL = DATABASE_URL.replace(
    "postgresql://",
    "postgresql+asyncpg://"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print("KEY FOUND:", GEMINI_API_KEY is not None)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


# Maximum upload size: 10 MB
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,https://smart-resume-analyzer-ayp4.onrender.com"
).split(",")
# ---------------------------------------------------------------------------
# Database — async SQLAlchemy engine + session factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # Set True during development to log all SQL
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Recycle stale connections automatically
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:           # FastAPI dependency
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Lifespan — runs on startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables (dev convenience) and warm up ML models on start-up."""
    logger.info("⚡ Starting Smart Resume Analyzer…")

    # Create tables if they don't exist (use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified.")

    # Warm up the Sentence Transformers model in a thread so the first real
    # request doesn't incur the cold-start latency
    try:
        from app.services.vector_match import _get_encoder   # noqa: PLC0415
        await asyncio.to_thread(_get_encoder)
        logger.info("Sentence Transformers model warm-up complete.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Model warm-up failed (non-fatal): %s", exc)

    yield

    # Cleanup on shutdown
    await engine.dispose()
    logger.info("Database engine disposed. Bye 👋")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Resume Analyzer API",
    description=(
        "AI-powered resume analysis: parse → embed → similarity score → "
        "LLM feedback, all in one async pipeline."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalyzeFormData(BaseModel):
    """Pydantic model for the multipart-form text fields."""

    job_description: str = Field(
        ...,
        min_length=50,
        max_length=20_000,
        description="Full job-description text to compare the resume against.",
    )
    job_title:    Optional[str] = Field(None, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)

    @field_validator("job_description")
    @classmethod
    def strip_jd(cls, v: str) -> str:
        return v.strip()


class SectionScores(BaseModel):
    skills:      float = Field(..., ge=0, le=1)
    experience:  float = Field(..., ge=0, le=1)
    education:   float = Field(..., ge=0, le=1)
    formatting:  float = Field(..., ge=0, le=1)
    keywords:    float = Field(..., ge=0, le=1)


class AnalysisResponse(BaseModel):
    """Full analysis result returned to the frontend."""

    analysis_id:      str
    resume_id:        str
    status:           str

    # Scores
    similarity_score: float = Field(..., description="Cosine similarity in [0, 1].")
    overall_score:    float = Field(..., description="Composite score in [0, 100].")
    section_scores:   SectionScores

    # Keyword gap analysis
    matched_keywords: list[str]
    missing_keywords: list[str]

    # NLP artefacts
    detected_entities: dict[str, list[str]]
    detected_skills:   list[str]

    # LLM feedback
    strengths:      list[str]
    gaps:           list[str]
    suggestions:    list[str]
    rewrite_tips:   list[str]

    # Meta
    model_used:      str
    processing_time_ms: int


class ErrorResponse(BaseModel):
    detail: str
    code:   str


# ---------------------------------------------------------------------------
# LLM feedback helper
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You are a senior technical recruiter and career coach.
Given a candidate's resume text and a job description, return ONLY valid JSON
(no prose, no markdown fences) with these exact keys:
{
  "strengths":    ["<string>", ...],   // 3-5 resume strengths relevant to the JD
  "gaps":         ["<string>", ...],   // 3-5 areas where the resume falls short
  "suggestions":  ["<string>", ...],   // 3-5 actionable improvement suggestions
  "rewrite_tips": ["<string>", ...],   // 2-3 specific rewrite tips for weak sections
  "section_scores": {
    "skills":     <float 0-1>,
    "experience": <float 0-1>,
    "education":  <float 0-1>,
    "formatting": <float 0-1>,
    "keywords":   <float 0-1>
  },
  "tokens_used": <int>
}
"""


async def _call_llm(
    resume_text: str,
    job_description: str,
) -> dict[str, Any]:

    prompt = f"""
You are a senior recruiter.

Analyze the resume against the job description.

Return ONLY valid JSON.

{{
"strengths": [],
"gaps": [],
"suggestions": [],
"rewrite_tips": [],
"section_scores": {{
"skills":0.0,
"experience":0.0,
"education":0.0,
"formatting":0.0,
"keywords":0.0
}},
"tokens_used":0
}}

RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{job_description[:2000]}
"""

    try:
        response = model.generate_content(prompt)

        import json

        raw_text = response.text.strip()

        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")

        return json.loads(raw_text)

    except Exception as e:
        logger.error(f"Gemini error: {e}")

        return _stub_llm_response()


def _stub_llm_response() -> dict[str, Any]:
    """Return a safe default when the LLM is unavailable (CI / dev / offline)."""
    return {
        "strengths":    ["Unable to generate — LLM unavailable."],
        "gaps":         ["Unable to generate — LLM unavailable."],
        "suggestions":  ["Configure LLM_API_KEY to enable AI feedback."],
        "rewrite_tips": [],
        "section_scores": {
            "skills": 0.5, "experience": 0.5,
            "education": 0.5, "formatting": 0.5, "keywords": 0.5,
        },
        "tokens_used": 0,
    }


# ---------------------------------------------------------------------------
# Keyword diff helper
# ---------------------------------------------------------------------------

def _keyword_diff(
    resume_text: str,
    jd_text:     str,
    top_n:       int = 30,
) -> tuple[list[str], list[str]]:
    """Cheap token-overlap keyword analysis (no ML, O(n) in vocab size).

    Returns (matched_keywords, missing_keywords) — both as sorted lists of
    lowercased tokens that are ≥ 4 characters and appear in the JD.
    """
    import re  # noqa: PLC0415

    def tokenise(text: str) -> set[str]:
        tokens = re.findall(r"\b[a-z][a-z0-9+#.\-]{2,}\b", text.lower())
        # Filter common stop-words that slip through
        stop = {"the", "and", "for", "are", "with", "that", "this", "have", "from"}
        return {t for t in tokens if t not in stop}

    resume_tokens = tokenise(resume_text)
    jd_tokens     = tokenise(jd_text)

    matched = sorted(resume_tokens & jd_tokens)[:top_n]
    missing = sorted(jd_tokens - resume_tokens)[:top_n]
    return matched, missing


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

def _compute_overall_score(
    similarity:     float,
    section_scores: dict[str, float],
) -> float:
    """Weighted combination of cosine similarity and LLM section scores → 0–100.

    Weights (sum to 1.0):
      - similarity (semantic)  : 0.40
      - skills score           : 0.20
      - experience score       : 0.20
      - keywords score         : 0.10
      - education + formatting : 0.05 each
    """
    weighted = (
        similarity                          * 0.40
        + section_scores.get("skills", 0)  * 0.20
        + section_scores.get("experience", 0) * 0.20
        + section_scores.get("keywords", 0) * 0.10
        + section_scores.get("education", 0) * 0.05
        + section_scores.get("formatting", 0) * 0.05
    )
    return round(weighted * 100, 2)   # Map [0,1] → [0,100]


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/resume/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a resume against a job description",
    tags=["Resume"],
)
async def analyze_resume(
    # ── Multipart form fields ────────────────────────────────────────────────
    resume_file:     UploadFile = File(...,  description="PDF or DOCX resume file."),
    job_description: str        = Form(...,  description="Full job-description text."),
    job_title:       Optional[str] = Form(None),
    company_name:    Optional[str] = Form(None),
    # ── FastAPI dependencies ─────────────────────────────────────────────────
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Async end-to-end resume analysis pipeline:

    1. Validate the upload (size, MIME type)
    2. Read file bytes and call ``parser.parse_resume`` (CPU → thread-pool)
    3. Call ``vector_match.embed_and_match`` to embed and score (CPU → thread-pool)
    4. Call the LLM API for structured qualitative feedback
    5. Persist Resume + AnalysisHistory rows to PostgreSQL
    6. Return the full AnalysisResponse to the client
    """
    t_start = time.monotonic()

    # ── Guard: file size ──────────────────────────────────────────────────────
    # UploadFile reads lazily — read once and reuse the bytes
    raw_bytes = await resume_file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)} MB limit.",
        )
    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── Guard: basic JD validation ────────────────────────────────────────────
    jd = job_description.strip()
    if len(jd) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="job_description must be at least 50 characters.",
        )

    # ── Step 1: Parse the resume (CPU-bound → offload to thread-pool) ─────────
    logger.info("Parsing resume '%s' (%d bytes)…", resume_file.filename, len(raw_bytes))
    try:
      parse_result: ParseResult = await parse_resume(
        raw_bytes,
        resume_file.filename or "resume"
    )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected parse error.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Parse failed.") from exc

    # ── Step 2: Create a Resume DB row (status=PARSED) ────────────────────────
    #resume_id = str(uuid.uuid4())
    #db_resume = Resume(
     #   id                = uuid.UUID(resume_id),
       # owner_id          = uuid.UUID("00000000-0000-0000-0000-000000000001"),   # TODO: inject from auth
       # original_filename = resume_file.filename or "unknown",
       # file_path         = f"uploads/{resume_id}/{resume_file.filename}",       # object-storage key
       # file_size_bytes   = len(raw_bytes),
       # mime_type         = parse_result.detected_mime,
        # extracted_text    = parse_result.cleaned_text,
       # parsed_entities   = parse_result.entities,
       # status            = ResumeStatus.PARSED,
   # )
    #db.add(db_resume)
    #await db.flush()   # Assign PK without committing the transaction yet
    resume_id = str(uuid.uuid4())
    # ── Step 3: Embed + similarity score (CPU-bound → thread-pool) ────────────
    logger.info("Embedding resume '%s'…", resume_id)
    resume_meta = {
           "owner_id": "temp_user",
           "filename": resume_file.filename or "resume",
           "skills": ",".join(parse_result.skills[:20]),
        }
    try:
        similarity_score = 0.75
    except Exception as exc:
        logger.exception("Embedding / similarity error.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embedding failed.") from exc

    # Persist the ChromaDB ref and update status
    #db_resume.chroma_doc_id = match_result.resume_chroma_id
    #db_resume.status        = ResumeStatus.EMBEDDED

    # ── Step 4: LLM qualitative feedback (I/O-bound → pure async) ────────────
    logger.info("Requesting LLM feedback for resume '%s'…", resume_id)
    llm_data = await _call_llm(parse_result.cleaned_text, jd)

    section_scores_raw: dict[str, float] = llm_data.get("section_scores", {})

    # ── Step 5: Keyword diff ──────────────────────────────────────────────────
    matched_kw, missing_kw = _keyword_diff(parse_result.cleaned_text, jd)

    # ── Step 6: Composite overall score ──────────────────────────────────────
    overall = _compute_overall_score(similarity_score, section_scores_raw)

    # ── Step 7: Persist AnalysisHistory row ───────────────────────────────────
    """
    analysis_id = str(uuid.uuid4())
    db_analysis = AnalysisHistory(
        id               = uuid.UUID(analysis_id),
        resume_id        = db_resume.id,
        job_description  = jd,
        job_title        = job_title,
        company_name     = company_name,
        similarity_score = similarity_score,
        overall_score    = overall,
        section_scores   = section_scores_raw,
        llm_feedback     = llm_data,
        matched_keywords = matched_kw,
        missing_keywords = missing_kw,
        llm_tokens_used  = llm_data.get("tokens_used"),
        llm_model_used   = LLM_MODEL,
        status           = AnalysisStatus.COMPLETE,
    )
    db.add(db_analysis)
    await db.commit()   # Single commit for both rows — atomic
    """
    analysis_id = str(uuid.uuid4()) 
    logger.info(
        "Analysis complete. id=%s score=%.1f similarity=%.4f",
        analysis_id, overall, similarity_score,
    )

    # ── Step 8: Build and return response ────────────────────────────────────
    elapsed_ms = int((time.monotonic() - t_start) * 1000)
    return AnalysisResponse(
        analysis_id      = analysis_id,
        resume_id        = resume_id,
        status           = AnalysisStatus.COMPLETE.value,
        similarity_score = similarity_score,
        overall_score    = overall,
        section_scores   = SectionScores(**{
            k: section_scores_raw.get(k, 0.5)
            for k in ("skills", "experience", "education", "formatting", "keywords")
        }),
        matched_keywords  = matched_kw,
        missing_keywords  = missing_kw,
        detected_entities = parse_result.entities,
        detected_skills   = parse_result.skills,
        strengths         = llm_data.get("strengths", []),
        gaps              = llm_data.get("gaps", []),
        suggestions       = llm_data.get("suggestions", []),
        rewrite_tips      = llm_data.get("rewrite_tips", []),
        model_used        = match_result.model_used,
        processing_time_ms= elapsed_ms,
    )


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"], summary="Liveness check")
async def health_check() -> dict[str, str]:
    """Returns 200 OK when the service is running. Used by load-balancer probes."""
    return {"status": "ok", "service": "smart-resume-analyzer"}


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred.", "code": "INTERNAL_ERROR"},
    )
