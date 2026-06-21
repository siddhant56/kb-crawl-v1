"""
auth_module/routers/upload.py
-----------------------------
Document upload endpoint for approved users with upload_access permission.

Supported formats: PDF, DOCX, TXT, MD

Pipeline per upload
-------------------
1. Validate file type and size (max 50 MB)
2. Convert to raw text → Markdown
3. Sanitize: strip API keys, PII, pricing data (regex-based)
4. Write sanitized .md to knowledge-base/uploads/
5. Chunk + embed → append to ChromaDB (incremental, no full rebuild)
6. Update TF-IDF BM25 index in-place
7. Return: chunks_added, redactions summary, filename

Routes
------
POST /api/upload   — upload a document (multipart/form-data)
GET  /api/upload/categories — list valid categories
"""

import hashlib
import io
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth_module.database import get_db
from auth_module.dependencies import require_upload_access
from auth_module.models import CustomCategory, DocumentUpload, User
from auth_module.sanitizer import sanitize

# Lowercase letters/digits/hyphens, must start with a letter, max 50 chars
_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9-]{0,49}$")

router = APIRouter(prefix="/api/upload", tags=["Document Upload"])

# ── Constants ────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",  # some browsers send this for .md
}

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "knowledge-base"

VALID_CATEGORIES = [
    "blog",
    "services",
    "hire-developers",
    "case-studies",
    "industries",
    "resources",
    "about",
    "company",
    "uploads",  # catch-all for user uploads without a specific category
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Turn a filename stem into a safe filesystem slug."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^\w\s\-]", "", name).strip().lower()
    name = re.sub(r"[\s_]+", "-", name)
    return name[:180] or "document"


def _pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


def _docx_to_text(data: bytes) -> str:
    import docx
    doc = docx.Document(io.BytesIO(data))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # Map heading styles to markdown headers
        style = para.style.name if para.style else ""
        if "Heading 1" in style:
            paragraphs.append(f"# {text}")
        elif "Heading 2" in style:
            paragraphs.append(f"## {text}")
        elif "Heading 3" in style:
            paragraphs.append(f"### {text}")
        elif "Heading 4" in style:
            paragraphs.append(f"#### {text}")
        else:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _to_markdown(raw_text: str, title: str) -> str:
    """Wrap raw extracted text in the standard markdown structure used by the scraper."""
    body = raw_text.strip()
    return f"# {title}\n\n---\n\n{body}\n"


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/history",
    summary="Upload audit trail",
    description="Returns all uploaded documents with uploader info. Super admins see everyone's uploads; users with upload_access see only their own.",
)
def upload_history(
    current_user: User = Depends(require_upload_access),
    db: Session = Depends(get_db),
) -> list:
    from auth_module.models import UserRole
    if current_user.role == UserRole.SUPER_ADMIN:
        records = db.query(DocumentUpload).order_by(DocumentUpload.uploaded_at.desc()).all()
    else:
        records = (
            db.query(DocumentUpload)
            .filter(DocumentUpload.user_id == current_user.id)
            .order_by(DocumentUpload.uploaded_at.desc())
            .all()
        )

    # Resolve uploader emails in one query
    user_ids = {r.user_id for r in records}
    users = {u.id: u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "saved_as": r.saved_as,
            "category": r.category,
            "chunks_added": r.chunks_added,
            "uploaded_by": users.get(r.user_id, f"user#{r.user_id}"),
            "uploaded_at": r.uploaded_at.isoformat(),
        }
        for r in records
    ]


@router.get(
    "/categories",
    summary="List valid document categories",
    description="Returns built-in categories plus any custom categories users have created.",
)
def list_categories(db: Session = Depends(get_db)) -> dict:
    custom = [r.name for r in db.query(CustomCategory.name).order_by(CustomCategory.name).all()]
    merged = VALID_CATEGORIES + [c for c in custom if c not in VALID_CATEGORIES]
    return {"categories": merged}


@router.post(
    "",
    summary="Upload a document to the knowledge base",
    description=(
        "Accepts PDF, DOCX, TXT, or MD files (max 50 MB). "
        "The document is converted to Markdown, sanitized of sensitive data "
        "(API keys, PII, pricing), then embedded and appended to the vector store. "
        "Requires upload_access permission."
    ),
)
def upload_document(
    file: UploadFile = File(..., description="Document file (PDF / DOCX / TXT / MD)"),
    category: str = Form(..., description=f"Category: one of {VALID_CATEGORIES}"),
    title: Optional[str] = Form(None, description="Optional title override (defaults to filename)"),
    current_user: User = Depends(require_upload_access),
    db: Session = Depends(get_db),
) -> JSONResponse:
    # ── Validate / register category ─────────────────────────────────────────
    if category not in VALID_CATEGORIES:
        if not _CATEGORY_RE.match(category):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid category name '{category}'. "
                    "Use only lowercase letters, digits, and hyphens (e.g. 'my-topic'). "
                    "Must start with a letter, max 50 characters."
                ),
            )
        # Persist new category so it appears for all users going forward
        if not db.query(CustomCategory).filter(CustomCategory.name == category).first():
            db.add(CustomCategory(
                name=category,
                created_by_id=current_user.id,
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()

    # ── Validate file extension ──────────────────────────────────────────────
    original_name = file.filename or "document"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Read and size-check ──────────────────────────────────────────────────
    data = file.file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the 50 MB limit ({len(data) / 1024 / 1024:.1f} MB uploaded).",
        )
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File is empty.")

    # ── Extract text ─────────────────────────────────────────────────────────
    try:
        if suffix == ".pdf":
            raw_text = _pdf_to_text(data)
        elif suffix == ".docx":
            raw_text = _docx_to_text(data)
        else:
            raw_text = data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse file: {exc}",
        )

    if len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted text is too short (< 50 characters). The file may be empty or image-only.",
        )

    # ── Convert to markdown ──────────────────────────────────────────────────
    doc_title = " ".join((title or Path(original_name).stem).split())
    markdown = raw_text if suffix == ".md" else _to_markdown(raw_text, doc_title)

    # ── Sanitize ─────────────────────────────────────────────────────────────
    clean_markdown, report = sanitize(markdown)

    # ── Deduplicate by content hash ───────────────────────────────────────────
    content_hash = hashlib.sha256(clean_markdown.encode()).hexdigest()
    existing = db.query(DocumentUpload).filter(DocumentUpload.content_hash == content_hash).first()
    if existing:
        uploader = db.query(User).filter(User.id == existing.user_id).first()
        uploader_label = uploader.email if uploader else f"user #{existing.user_id}"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This document is already in the knowledge base. "
                f"Uploaded by {uploader_label} on "
                f"{existing.uploaded_at.strftime('%Y-%m-%d')} "
                f"as '{existing.filename}' in category '{existing.category}'."
            ),
        )

    # ── Persist sanitized markdown to knowledge-base/ ────────────────────────
    category_dir = KNOWLEDGE_BASE_PATH / category
    category_dir.mkdir(parents=True, exist_ok=True)

    # Include user ID so two users uploading the same filename don't collide.
    # Same user re-uploading the same file will still overwrite their own version.
    slug = f"u{current_user.id}-" + _slugify(Path(original_name).stem)
    md_path = category_dir / f"{slug}.md"
    md_path.write_text(clean_markdown, encoding="utf-8")

    # ── Embed and append to vector store ─────────────────────────────────────
    try:
        from pro_implementation.ingest import append_document
        result = append_document({
            "type": category,
            "source": md_path.as_posix(),
            "text": clean_markdown,
        })
    except Exception as exc:
        md_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding failed: {exc}",
        )

    # ── Save audit record ─────────────────────────────────────────────────────
    db.add(DocumentUpload(
        user_id=current_user.id,
        filename=original_name,
        saved_as=str(md_path.relative_to(KNOWLEDGE_BASE_PATH.parent)),
        category=category,
        content_hash=content_hash,
        chunks_added=result["chunks_added"],
        uploaded_at=datetime.now(timezone.utc),
    ))
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "filename": original_name,
            "saved_as": md_path.name,
            "category": category,
            "chunks_added": result["chunks_added"],
            "chunks_replaced": result["chunks_removed"],
            "sanitization": {
                "redactions_total": report.total,
                "by_category": report.by_category,
            },
            "uploaded_by": current_user.email,
        },
    )
