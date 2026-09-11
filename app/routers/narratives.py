"""Narrative capture route - multipart audio upload -> Sarvam STT -> DB row.
ASSUMPTION: transcribe_and_translate() returns dict with keys:
transcript_original, transcript_english, detected_language, confidence.
Verify against app/services/sarvam_stt.py - fix key names here if they differ.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Narrative
from app.services.sarvam_stt import transcribe_and_translate

router = APIRouter(prefix="/narratives", tags=["narratives"])

AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/webm"}


@router.post("/")
async def create_narrative(
    patient_id: uuid.UUID,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if audio.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, f"Unsupported audio type: {audio.content_type}")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file")

    file_id = uuid.uuid4()
    ext = Path(audio.filename or "").suffix or ".wav"
    audio_path = AUDIO_DIR / f"{file_id}{ext}"
    audio_path.write_bytes(audio_bytes)

    try:
        stt_result = await transcribe_and_translate(audio_path)
    except Exception as exc:
        raise HTTPException(502, f"STT call failed: {exc}") from exc

    narrative = Narrative(
        patient_id=patient_id,
        transcript_original=stt_result.get("transcript_original"),
        transcript_english=stt_result.get("transcript_english"),
        detected_language=stt_result.get("detected_language"),
        confidence=stt_result.get("confidence"),
        audio_ref=str(audio_path),
        status="captured",
    )
    db.add(narrative)
    db.commit()
    db.refresh(narrative)

    return {
        "id": narrative.id,
        "patient_id": narrative.patient_id,
        "status": narrative.status,
        "transcript_original": narrative.transcript_original,
        "transcript_english": narrative.transcript_english,
        "detected_language": narrative.detected_language,
        "confidence": narrative.confidence,
        "created_at": narrative.created_at,
    }
