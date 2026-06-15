"""
services/parser.py — Document ingestion & NLP entity extraction.

Pipeline (called by main.py):
  1. Detect MIME type from file bytes / filename extension
  2. Dispatch to the appropriate text-extractor (PDF → pdfminer, DOCX → python-docx)
  3. Clean & normalise the raw text
  4. Run the cleaned text through a spaCy pipeline for NER + section detection
  5. Return a structured ParseResult dataclass consumed by the API layer

Dependencies (add to requirements.txt):
    pdfminer.six>=20221105
    python-docx>=1.1.0
    spacy>=3.7.0
    # python -m spacy download en_core_web_lg   (or sm/md)
"""

from __future__ import annotations

import io
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Optional

import spacy
from spacy.language import Language

# pdfminer — lazy import so the service can still load if only DOCX is needed
try:
    from pdfminer.high_level import extract_text as pdf_extract_text
    from pdfminer.pdfdocument import PDFPasswordIncorrect
    _PDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PDF_AVAILABLE = False

# python-docx — likewise lazy
try:
    from docx import Document as DocxDocument
    _DOCX_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DOCX_AVAILABLE = False


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy model — loaded once at module import time (expensive operation)
# ---------------------------------------------------------------------------

_NLP_MODEL: Optional[Language] = None

def _get_nlp() -> Language:
    """Lazy-load the spaCy model and cache it in the module-level singleton.

    Using ``en_core_web_lg`` gives the best NER accuracy; swap to
    ``en_core_web_sm`` for lower memory footprint in resource-constrained
    environments.
    """
    global _NLP_MODEL
    if _NLP_MODEL is None:
        model_name = "en_core_web_sm"
        try:
            _NLP_MODEL = spacy.load(model_name)
            logger.info("spaCy model '%s' loaded successfully.", model_name)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{model_name}' not found. "
                f"Run: python -m spacy download {model_name}"
            ) from exc
    return _NLP_MODEL


# ---------------------------------------------------------------------------
# Result dataclass — typed contract between parser and callers
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """Structured output of the parsing pipeline.

    Attributes:
        raw_text:        Full extracted plain-text (pre-clean).
        cleaned_text:    Normalised text fed into spaCy.
        entities:        NER output grouped by label,
                         e.g. {"ORG": ["Google", "MIT"], "DATE": ["2021"]}.
        skills:          Heuristically detected skill tokens (lowercased).
        section_map:     Detected resume sections → their text content,
                         e.g. {"EXPERIENCE": "...", "EDUCATION": "..."}.
        word_count:      Token count of cleaned_text.
        char_count:      Character count of cleaned_text.
        detected_mime:   MIME type inferred from content, e.g. 'application/pdf'.
        parse_warnings:  Non-fatal issues encountered during extraction.
    """

    raw_text:       str
    cleaned_text:   str
    entities:       dict[str, list[str]]     = field(default_factory=dict)
    skills:         list[str]                = field(default_factory=list)
    section_map:    dict[str, str]           = field(default_factory=dict)
    word_count:     int                      = 0
    char_count:     int                      = 0
    detected_mime:  str                      = "application/octet-stream"
    parse_warnings: list[str]                = field(default_factory=list)


# ---------------------------------------------------------------------------
# MIME / format detection
# ---------------------------------------------------------------------------

_MAGIC_PDF  = b"%PDF"
_MAGIC_DOCX = b"PK\x03\x04"   # ZIP-based OOXML format


def _detect_mime(data: bytes, filename: str) -> str:
    """Inspect the first few bytes (magic numbers) to determine file type.

    Falls back to filename extension when magic bytes are inconclusive.
    """
    if data[:4] == _MAGIC_PDF:
        return "application/pdf"
    if data[:4] == _MAGIC_DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    # Extension fallback
    suffix = Path(filename).suffix.lower()
    _ext_map = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc":  "application/msword",
        ".txt":  "text/plain",
    }
    return _ext_map.get(suffix, "application/octet-stream")


# ---------------------------------------------------------------------------
# Text extractors
# ---------------------------------------------------------------------------

def _extract_from_pdf(data: bytes) -> tuple[str, list[str]]:
    """Extract all text from a PDF byte payload using pdfminer.six.

    Returns (raw_text, warnings).
    """
    if not _PDF_AVAILABLE:
        raise RuntimeError("pdfminer.six is not installed.")
    warnings: list[str] = []
    try:
        raw = pdf_extract_text(io.BytesIO(data))
    except PDFPasswordIncorrect:
        raise ValueError("The uploaded PDF is password-protected.")
    except Exception as exc:
        raise ValueError(f"PDF extraction failed: {exc}") from exc

    if not raw or not raw.strip():
        warnings.append("PDF yielded no extractable text; it may be scanned/image-only.")
    return raw or "", warnings


def _extract_from_docx(data: bytes) -> tuple[str, list[str]]:
    """Extract all paragraph text from a DOCX byte payload using python-docx.

    Returns (raw_text, warnings).
    """
    if not _DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed.")
    warnings: list[str] = []
    try:
        doc = DocxDocument(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        raw = "\n".join(paragraphs)
    except Exception as exc:
        raise ValueError(f"DOCX extraction failed: {exc}") from exc

    if not raw.strip():
        warnings.append("DOCX yielded no paragraph text.")
    return raw, warnings


def _extract_from_txt(data: bytes) -> tuple[str, list[str]]:
    """Decode a plain-text file, trying UTF-8 then latin-1."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding), []
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), ["Text decoded with replacement characters."]


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

# Patterns compiled once for performance
_WHITESPACE_RE  = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_NON_PRINT_RE   = re.compile(r"[^\x20-\x7E\n]")   # strips non-ASCII control chars


def _clean_text(text: str) -> str:
    """Normalise extracted text for downstream NLP processing.

    Steps:
      1. Strip non-printable / non-ASCII control characters
      2. Collapse runs of spaces/tabs to a single space
      3. Collapse runs of 3+ blank lines to two
      4. Strip leading/trailing whitespace
    """
    text = _NON_PRINT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Resume section detection
# ---------------------------------------------------------------------------

# Common section headings found in resumes — order matters (first match wins)
_SECTION_HEADERS: list[tuple[str, re.Pattern[str]]] = [
    ("SUMMARY",     re.compile(r"^(summary|profile|objective|about me)\s*$",      re.I | re.M)),
    ("EXPERIENCE",  re.compile(r"^(experience|work experience|employment|career)", re.I | re.M)),
    ("EDUCATION",   re.compile(r"^(education|academic|qualifications)",            re.I | re.M)),
    ("SKILLS",      re.compile(r"^(skills|technical skills|core competencies)",    re.I | re.M)),
    ("PROJECTS",    re.compile(r"^(projects|personal projects|portfolio)",         re.I | re.M)),
    ("CERTIFICATIONS", re.compile(r"^(certifications?|licenses?|accreditations?)", re.I | re.M)),
    ("AWARDS",      re.compile(r"^(awards?|honors?|achievements?)",                re.I | re.M)),
    ("PUBLICATIONS",re.compile(r"^(publications?|papers?|research)",               re.I | re.M)),
]


def _detect_sections(text: str) -> dict[str, str]:
    """Split the cleaned resume text into labelled sections.

    Uses regex heading detection; returns a dict mapping section label to its
    content block (stripped).  Unclassified content lands in "MISC".
    """
    # Find all header positions
    hits: list[tuple[int, str]] = []
    for label, pattern in _SECTION_HEADERS:
        for match in pattern.finditer(text):
            hits.append((match.start(), label))

    if not hits:
        return {"MISC": text}

    # Sort by position, then extract spans
    hits.sort(key=lambda x: x[0])
    sections: dict[str, str] = {}
    for i, (start, label) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        content = text[start:end].strip()
        # If the same section header appears twice, concatenate
        sections[label] = (sections.get(label, "") + "\n" + content).strip()

    # Anything before the first header
    if hits[0][0] > 0:
        sections["HEADER"] = text[: hits[0][0]].strip()

    return sections


# ---------------------------------------------------------------------------
# Skill extraction heuristic
# ---------------------------------------------------------------------------

# A curated seed list; extend this or replace with a dedicated skill taxonomy
# (e.g. ESCO, LinkedIn skills ontology) for production use.
_SKILL_SEEDS: frozenset[str] = frozenset({
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "node.js", "fastapi", "django", "flask",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "terraform", "aws", "gcp", "azure",
    "machine learning", "deep learning", "nlp", "computer vision",
    "scikit-learn", "pytorch", "tensorflow", "pandas", "numpy",
    "git", "ci/cd", "agile", "scrum", "rest", "graphql",
    "linux", "bash", "spark", "kafka", "airflow",
})


def _extract_skills(text: str) -> list[str]:
    """Return a deduplicated list of recognised skill tokens found in *text*.

    Simple substring search against ``_SKILL_SEEDS`` — good enough as a first
    pass; replace with an ML-based extractor (e.g. a fine-tuned NER model) for
    higher recall in production.
    """
    lower = text.lower()
    return sorted({skill for skill in _SKILL_SEEDS if skill in lower})


# ---------------------------------------------------------------------------
# spaCy NER
# ---------------------------------------------------------------------------

# Labels we care about for resume analysis
_RELEVANT_LABELS: frozenset[str] = frozenset({
    "PERSON", "ORG", "GPE", "DATE", "MONEY", "PRODUCT", "WORK_OF_ART", "FAC",
})


def _run_ner(text: str) -> dict[str, list[str]]:
    """Run spaCy NER on *text* and return entities grouped by label.

    Only ``_RELEVANT_LABELS`` are retained to keep the payload compact.
    Duplicates within each label bucket are removed.
    """
    nlp = _get_nlp()

    # spaCy has a default max_length of 1 000 000 chars; truncate safely
    truncated = text[:900_000] if len(text) > 900_000 else text

    doc = nlp(truncated)
    grouped: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for ent in doc.ents:
        if ent.label_ not in _RELEVANT_LABELS:
            continue
        key = (ent.label_, ent.text.strip())
        if key in seen:
            continue
        seen.add(key)
        grouped[ent.label_].append(ent.text.strip())

    return dict(grouped)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def parse_resume(
    file_data: bytes,
    filename:  str,
) -> ParseResult:
    """Top-level coroutine — orchestrates the full parsing pipeline.

    Args:
        file_data:  Raw bytes of the uploaded file.
        filename:   Original filename (used for MIME fallback detection).

    Returns:
        A :class:`ParseResult` instance with all extracted fields populated.

    Raises:
        ValueError: If the file type is unsupported or extraction fails.
    """
    warnings: list[str] = []

    # ── 1. Detect MIME type ───────────────────────────────────────────────────
    mime = _detect_mime(file_data, filename)
    logger.debug("Detected MIME '%s' for file '%s'.", mime, filename)

    # ── 2. Extract raw text ───────────────────────────────────────────────────
    if mime == "application/pdf":
        raw_text, ext_warnings = _extract_from_pdf(file_data)
    elif "wordprocessingml" in mime or mime == "application/msword":
        raw_text, ext_warnings = _extract_from_docx(file_data)
    elif mime == "text/plain":
        raw_text, ext_warnings = _extract_from_txt(file_data)
    else:
        raise ValueError(
            f"Unsupported file type '{mime}'. "
            "Please upload a PDF, DOCX, or plain-text resume."
        )

    warnings.extend(ext_warnings)

    # ── 3. Clean & normalise ─────────────────────────────────────────────────
    cleaned = _clean_text(raw_text)

    if len(cleaned) < 50:
        warnings.append(
            f"Cleaned text is very short ({len(cleaned)} chars); "
            "extraction quality may be poor."
        )
        logger.warning("Short extraction for '%s': %d chars.", filename, len(cleaned))

    # ── 4. Section detection ─────────────────────────────────────────────────
    # Done before NER so section-aware context can guide downstream processing
    section_map = _detect_sections(cleaned)
    logger.debug("Detected sections: %s", list(section_map.keys()))

    # ── 5. spaCy NER (CPU-bound — run in default thread pool in production) ──
    # NOTE: For true async use, wrap with asyncio.to_thread(run_ner, cleaned)
    entities = _run_ner(cleaned)
    logger.debug(
        "NER complete — %d entity types, %d total entities.",
        len(entities),
        sum(len(v) for v in entities.values()),
    )

    # ── 6. Skill extraction ───────────────────────────────────────────────────
    # Prefer the SKILLS section text if detected, else fall back to full text
    skills_source = section_map.get("SKILLS", cleaned)
    skills = _extract_skills(skills_source)

    # ── 7. Assemble result ────────────────────────────────────────────────────
    return ParseResult(
        raw_text      = raw_text,
        cleaned_text  = cleaned,
        entities      = entities,
        skills        = skills,
        section_map   = section_map,
        word_count    = len(cleaned.split()),
        char_count    = len(cleaned),
        detected_mime = mime,
        parse_warnings= warnings,
    )
