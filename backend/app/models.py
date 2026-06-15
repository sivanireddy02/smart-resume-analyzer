"""
models.py — SQLAlchemy ORM models for Smart Resume Analyzer.

Data flow:
  User (1) ──< Resume (N) ──< AnalysisHistory (N)

Each Resume maps to a raw file + extracted text. Each AnalysisHistory row
stores one analysis run: the job-description text used, similarity score,
extracted entities, and the raw LLM feedback JSON.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Project-wide declarative base."""
    pass


class TimestampMixin:
    """Injects server-side UTC created_at / updated_at into every model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ResumeStatus(str, enum.Enum):
    """Lifecycle states for an uploaded resume."""
    PENDING  = "pending"   # Uploaded, not yet parsed
    PARSED   = "parsed"    # Text extracted + spaCy entities ready
    EMBEDDED = "embedded"  # Sentence-Transformer vector in ChromaDB
    FAILED   = "failed"    # Unrecoverable error


class AnalysisStatus(str, enum.Enum):
    """Completion states for a single analysis run."""
    QUEUED   = "queued"
    RUNNING  = "running"
    COMPLETE = "complete"
    FAILED   = "failed"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(TimestampMixin, Base):
    """Registered application user.

    Passwords are stored as bcrypt hashes — never plain-text.
    ``is_active=False`` soft-disables an account without deleting it.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), nullable=False,  # RFC 5321 max length
        doc="Unique login e-mail address.",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False,
        doc="bcrypt hash — never store plain-text.",
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # One user → many resumes
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class Resume(TimestampMixin, Base):
    """A single resume document uploaded by a user.

    Raw bytes are persisted in object storage (S3/GCS); only the storage key
    and extracted text live in Postgres. The ``chroma_doc_id`` ties this row
    to its embedding vector in ChromaDB.
    """

    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_owner_id", "owner_id"),
        Index("ix_resumes_status",   "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK → users.id — the uploader.",
    )

    # ── File metadata ────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(1024), nullable=False,
        doc="Object-storage key where the raw file lives.",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Parsed content — populated by services/parser.py ────────────────────
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        doc="Full plain-text extracted from the document.",
    )
    parsed_entities: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        doc="spaCy NER output: {label: [entity_text, ...], ...}.",
    )

    # ── Vector store ref — populated by services/vector_match.py ────────────
    chroma_doc_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True,
        doc="ChromaDB document ID for this resume's sentence-transformer embedding.",
    )

    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus, name="resume_status"),
        default=ResumeStatus.PENDING,
        nullable=False,
    )
    error_detail: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        doc="Human-readable error when status=FAILED.",
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="resumes")
    analyses: Mapped[List["AnalysisHistory"]] = relationship(
        "AnalysisHistory",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="AnalysisHistory.created_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<Resume id={self.id} file={self.original_filename!r} "
            f"status={self.status.value}>"
        )


# ---------------------------------------------------------------------------
# AnalysisHistory
# ---------------------------------------------------------------------------

class AnalysisHistory(TimestampMixin, Base):
    """One analysis run: resume ↔ job-description comparison.

    Captures the full audit trail — scores, LLM feedback, keyword diffs,
    and token-usage for billing visibility — so previous runs can be replayed
    in the UI without re-running the pipeline.
    """

    __tablename__ = "analysis_history"
    __table_args__ = (
        Index("ix_analysis_resume_id",  "resume_id"),
        Index("ix_analysis_status",     "status"),
        Index("ix_analysis_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Job description submitted by the user ────────────────────────────────
    job_description: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="Raw JD text pasted or uploaded by the user.",
    )
    job_title:    Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Scores — all floats; similarity in [0,1], overall in [0,100] ─────────
    similarity_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        doc="Cosine similarity between resume & JD embeddings (0–1).",
    )
    overall_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        doc="Weighted composite: similarity + LLM rubric, mapped to 0–100.",
    )

    # Per-dimension breakdown → radar / bar chart on the frontend
    section_scores: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        doc=(
            "E.g. {'skills': 0.82, 'experience': 0.71, "
            "'education': 0.65, 'formatting': 0.90, 'keywords': 0.78}."
        ),
    )

    # ── Raw LLM output — kept for debugging and UI re-render ─────────────────
    llm_feedback: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        doc=(
            "Structured LLM response: "
            "{'strengths': [...], 'gaps': [...], 'suggestions': [...], "
            "'rewrite_tips': [...]}."
        ),
    )

    # Keyword diff surfaces the ATS-optimization insights
    matched_keywords: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        doc="Keywords present in both resume and JD.",
    )
    missing_keywords: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True,
        doc="JD keywords absent from the resume — highest-value suggestions.",
    )

    # ── LLM cost accounting ───────────────────────────────────────────────────
    llm_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_model_used:  Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.QUEUED,
        nullable=False,
    )
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resume: Mapped["Resume"] = relationship("Resume", back_populates="analyses")

    def __repr__(self) -> str:
        return (
            f"<AnalysisHistory id={self.id} resume_id={self.resume_id} "
            f"score={self.overall_score} status={self.status.value}>"
        )
