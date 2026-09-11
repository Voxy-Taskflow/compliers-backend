"""D-01/D-02: Document upload + OCR extraction route.
Upload image -> save locally -> run OCR (Gemini) -> store Document row,
status always "pending_review" (mirrors H-03 pattern for consistency).
"""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, Patient
from app.services.ocr_service import extract_text_from_image, OCRError

router = APIRouter()

UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/")
async def placeholder():
    return {"detail": "documents router alive"}


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

    return {
        "id": document.id,
        "patient_id": document.patient_id,
        "source_image_ref": document.source_image_ref,
        "extracted_text": document.extracted_text,
        "status": document.status,
        "created_at": document.created_at,
    }
