"""V-02/V-03: Narrative capture - text bypass (create_narrative) and real voice
capture via Sarvam STT (create_narrative_from_voice).
Summarization lives in app/routers/summaries.py, not here - avoid duplicate routes.
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Narrative, Patient
from app.services.sarvam_stt import transcribe_and_translate, SarvamSTTError

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "narratives router alive"}


class CreateNarrativeRequest(BaseModel):
    patient_id: uuid.UUID
    transcript_english: str
    transcript_original: str | None = None
    detected_language: str | None = None


@router.post("/")
async def create_narrative(
    body: CreateNarrativeRequest,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if patient is None:
        raise HTTPException(404, "Patient not found")

    if not body.transcript_english.strip():
        raise HTTPException(400, "transcript_english cannot be empty")

    narrative = Narrative(
        patient_id=patient.id,
        transcript_original=body.transcript_original,
        transcript_english=body.transcript_english,
        detected_language=body.detected_language,
        status="confirmed",
    )
    db.add(narrative)
    db.commit()
    db.refresh(narrative)

    return {
        "id": narrative.id,
        "patient_id": narrative.patient_id,
        "transcript_english": narrative.transcript_english,
        "status": narrative.status,
        "created_at": narrative.created_at,
    }


@router.post("/voice")
async def create_narrative_from_voice(
    patient_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(404, "Patient not found")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file")

    try:
        result = await transcribe_and_translate(audio_bytes, filename=file.filename or "recording.webm")
    except SarvamSTTError as exc:
        raise HTTPException(exc.status_code or 502, f"STT failed: {exc.message}") from exc

    if not result["transcript"].strip():
        raise HTTPException(422, "STT returned an empty transcript - audio may be silent or unclear")

    narrative = Narrative(
        patient_id=patient.id,
        transcript_english=result["transcript"],
        detected_language=result["detected_language"],
        confidence=result["language_probability"],
        audio_ref=None,  # not persisting raw audio to disk yet - add if needed later
        status="confirmed",
    )
    db.add(narrative)
    db.commit()
    db.refresh(narrative)

    return {
        "id": narrative.id,
        "patient_id": narrative.patient_id,
        "transcript_english": narrative.transcript_english,
        "detected_language": narrative.detected_language,
        "confidence": narrative.confidence,
        "status": narrative.status,
        "created_at": narrative.created_at,
    }
