"""F-0x: Followup proposals (RAG-generation bypassed for now — proposal_text supplied
directly by caller, same bypass pattern as narrative STT). Human approval required
before a followup can be scheduled (status: pending_approval -> approved/rejected).

POST /followups              - create a followup proposal
GET  /followups               - list followups, optional ?status= filter
GET  /followups/{id}          - fetch one
POST /followups/{id}/approve  - staff approves (staff_id in body - no real auth wired yet)
POST /followups/{id}/reject   - staff rejects
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Followup, Patient, Staff

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "followups router alive"}


class CreateFollowupRequest(BaseModel):
    patient_id: uuid.UUID
    query_text: str | None = None
    proposal_text: str
    rag_context: dict | None = None


class ApproveRejectRequest(BaseModel):
    staff_id: uuid.UUID


@router.post("/")
async def create_followup(
    body: CreateFollowupRequest,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if patient is None:
        raise HTTPException(404, "Patient not found")

    if not body.proposal_text.strip():
        raise HTTPException(400, "proposal_text cannot be empty")

    followup = Followup(
        patient_id=patient.id,
        query_text=body.query_text,
        proposal_text=body.proposal_text,
        rag_context=body.rag_context,
        status="pending_approval",
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)

    return _serialize(followup)


@router.get("")
@router.get("/list")
async def list_followups(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Followup)
    if status:
        q = q.filter(Followup.status == status)
    followups = q.order_by(Followup.created_at.desc()).all()
    return [_serialize(f) for f in followups]


@router.get("/{followup_id}")
async def get_followup(
    followup_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    followup = db.query(Followup).filter(Followup.id == followup_id).first()
    if followup is None:
        raise HTTPException(404, "Followup not found")
    return _serialize(followup)


@router.post("/{followup_id}/approve")
async def approve_followup(
    followup_id: uuid.UUID,
    body: ApproveRejectRequest,
    db: Session = Depends(get_db),
):
    followup = db.query(Followup).filter(Followup.id == followup_id).first()
    if followup is None:
        raise HTTPException(404, "Followup not found")
    if followup.status != "pending_approval":
        raise HTTPException(400, f"Followup is '{followup.status}', not pending_approval")

    staff = db.query(Staff).filter(Staff.id == body.staff_id).first()
    if staff is None:
        raise HTTPException(404, "Staff not found")

    followup.status = "approved"
    followup.approved_by = staff.id
    followup.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(followup)

    return _serialize(followup)


@router.post("/{followup_id}/reject")
async def reject_followup(
    followup_id: uuid.UUID,
    body: ApproveRejectRequest,
    db: Session = Depends(get_db),
):
    followup = db.query(Followup).filter(Followup.id == followup_id).first()
    if followup is None:
        raise HTTPException(404, "Followup not found")
    if followup.status != "pending_approval":
        raise HTTPException(400, f"Followup is '{followup.status}', not pending_approval")

    staff = db.query(Staff).filter(Staff.id == body.staff_id).first()
    if staff is None:
        raise HTTPException(404, "Staff not found")

    followup.status = "rejected"
    followup.approved_by = staff.id
    followup.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(followup)

    return _serialize(followup)


def _serialize(f: Followup) -> dict:
    return {
        "id": f.id,
        "patient_id": f.patient_id,
        "query_text": f.query_text,
        "rag_context": f.rag_context,
        "proposal_text": f.proposal_text,
        "status": f.status,
        "approved_by": f.approved_by,
        "approved_at": f.approved_at,
        "calendar_event_id": f.calendar_event_id,
        "created_at": f.created_at,
    }
