import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Patient, Summary, Narrative
from app.services.chat import generate_chat_response

router = APIRouter()

class ChatRequest(BaseModel):
    patient_id: uuid.UUID
    message: str

@router.post("/")
async def chat_endpoint(
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Get the latest summary as context
    summary = (
        db.query(Summary)
        .join(Narrative, Summary.narrative_id == Narrative.id)
        .filter(Narrative.patient_id == patient.id)
        .order_by(Summary.created_at.desc())
        .first()
    )
    context = {}
    if summary:
        context["facts"] = summary.facts_json
        context["interpretation"] = summary.interpretation_text
    
    try:
        response_data = await generate_chat_response(context, body.message)
    except Exception as e:
        raise HTTPException(500, f"Error generating chat response: {str(e)}")

    return response_data
