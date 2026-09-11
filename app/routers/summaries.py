"""Route: trigger NLP summarization for a captured narrative (N-05).
Wires: Narrative.transcript_english -> fact_extraction + interpretation (N-01/02/03)
-> schema validation with retry (N-04) -> risk-gate (H-01/H-02) -> Summary row,
status ALWAYS "pending_review" (H-03). No auto-finalization path exists here.

Also exposes /summaries list/get/review for the human-review queue.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Narrative, Summary, Staff
from app.services.fact_extraction import extract_facts
from app.services.interpretation import interpret_facts
from app.services.nlp_validation import call_with_retry, FACTS_SCHEMA, INTERPRETATION_SCHEMA, NLPValidationError
from app.services.risk_gate import apply_risk_gate

router = APIRouter(prefix="/narratives", tags=["narratives"])


@router.post("/{narrative_id}/summarize")
async def summarize_narrative(narrative_id: uuid.UUID, db: Session = Depends(get_db)):
    narrative = db.query(Narrative).filter(Narrative.id == narrative_id).first()
    if narrative is None:
        raise HTTPException(404, "Narrative not found")
    if not narrative.transcript_english:
        raise HTTPException(400, "Narrative has no English transcript yet - STT step incomplete")

    try:
        facts = await call_with_retry(extract_facts, FACTS_SCHEMA, narrative.transcript_english)
        interpretation = await call_with_retry(interpret_facts, INTERPRETATION_SCHEMA, facts)
    except NLPValidationError as exc:
        raise HTTPException(502, f"NLP pipeline failed validation: {exc}") from exc

    gate_result = apply_risk_gate(facts, interpretation, transcript_confidence=narrative.confidence)

    summary = Summary(
        narrative_id=narrative.id,
        facts_json=facts,
        interpretation_text=interpretation["interpretation_text"],
        status="pending_review",  # H-03: NEVER anything else here, no auto-finalization
        flagged=gate_result["flagged"],
        flag_reasons=gate_result["flag_reasons"],
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return _serialize_summary(summary)


summaries_router = APIRouter(prefix="/summaries", tags=["summaries"])


@summaries_router.get("/")
async def list_summaries(
    status: str | None = Query(default=None),
    flagged: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Summary)
    if status:
        q = q.filter(Summary.status == status)
    if flagged is not None:
        q = q.filter(Summary.flagged == flagged)
    summaries = q.order_by(Summary.created_at.desc()).all()
    return [_serialize_summary(s) for s in summaries]


@summaries_router.get("/{summary_id}")
async def get_summary(summary_id: uuid.UUID, db: Session = Depends(get_db)):
    summary = db.query(Summary).filter(Summary.id == summary_id).first()
    if summary is None:
        raise HTTPException(404, "Summary not found")
    return _serialize_summary(summary)


class ReviewSummaryRequest(BaseModel):
    staff_id: uuid.UUID
    decision: str  # 'reviewed' | 'actioned' | 'rejected'


@summaries_router.post("/{summary_id}/review")
async def review_summary(
    summary_id: uuid.UUID,
    body: ReviewSummaryRequest,
    db: Session = Depends(get_db),
):
    if body.decision not in ("reviewed", "actioned", "rejected"):
        raise HTTPException(400, "decision must be one of: reviewed, actioned, rejected")

    summary = db.query(Summary).filter(Summary.id == summary_id).first()
    if summary is None:
        raise HTTPException(404, "Summary not found")

    staff = db.query(Staff).filter(Staff.id == body.staff_id).first()
    if staff is None:
        raise HTTPException(404, "Staff not found")

    summary.status = body.decision
    summary.reviewed_by = staff.id
    summary.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(summary)

    return _serialize_summary(summary)


def _serialize_summary(s: Summary) -> dict:
    return {
        "id": s.id,
        "narrative_id": s.narrative_id,
        "status": s.status,
        "facts_json": s.facts_json,
        "interpretation_text": s.interpretation_text,
        "flagged": s.flagged,
        "flag_reasons": s.flag_reasons,
        "reviewed_by": s.reviewed_by,
        "reviewed_at": s.reviewed_at,
        "created_at": s.created_at,
    }
