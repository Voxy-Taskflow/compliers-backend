"""D-01/D-02: Document upload + OCR extraction route.
Upload image -> save locally -> run OCR (Gemini) -> store Document row,
status always "pending_review" (mirrors H-03 pattern for consistency).

Also exposes list/get/review for the human-review queue.
Note: Document has no reviewed_by/reviewed_at columns (unlike Summary) -
only status can be updated here, per current schema.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, Patient
from app.services.ocr_service import extract_text_from_image, OCRError

router = APIRouter()

UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/")
async def list_documents(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Document)
    if status:
        q = q.filter(Document.status == status)
    documents = q.order_by(Document.created_at.desc()).all()
    return [_serialize(d) for d in documents]


@router.post("/upload")
async def upload_document(
    patient_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(404, "Patient not found")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = uuid.uuid4()
    save_path = UPLOAD_DIR / f"{file_id}.{ext}"
    with open(save_path, "wb") as f:
        f.write(image_bytes)

    try:
        extracted_text = await extract_text_from_image(image_bytes, mime_type=file.content_type)
    except OCRError as exc:
        raise HTTPException(502, f"OCR failed: {exc}") from exc

    document = Document(
        patient_id=patient.id,
        source_image_ref=str(save_path),
        extracted_text=extracted_text,
        status="pending_review",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _serialize(document)


@router.get("/{document_id}")
async def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(404, "Document not found")
    return _serialize(document)


class ReviewDocumentRequest(BaseModel):
    decision: str  # 'reviewed' | 'actioned' | 'rejected'


@router.post("/{document_id}/review")
async def review_document(
    document_id: uuid.UUID,
    body: ReviewDocumentRequest,
    db: Session = Depends(get_db),
):
    if body.decision not in ("reviewed", "actioned", "rejected"):
        raise HTTPException(400, "decision must be one of: reviewed, actioned, rejected")

    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(404, "Document not found")

    document.status = body.decision
    db.commit()
    db.refresh(document)

    return _serialize(document)


def _serialize(d: Document) -> dict:
    return {
        "id": d.id,
        "patient_id": d.patient_id,
        "source_image_ref": d.source_image_ref,
        "extracted_text": d.extracted_text,
        "simplified_text": d.simplified_text,
        "translated_text": d.translated_text,
        "hallucination_flagged": d.hallucination_flagged,
        "status": d.status,
        "created_at": d.created_at,
    }
