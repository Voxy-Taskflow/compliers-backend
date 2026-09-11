"""Aggregate view for the human-review dashboard: everything currently
awaiting staff action, across summaries, documents, and followups.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Summary, Document, Followup

router = APIRouter()


@router.get("/")
async def get_review_queue(db: Session = Depends(get_db)):
    summaries = (
        db.query(Summary)
        .filter(Summary.status == "pending_review")
        .order_by(Summary.created_at.desc())
        .all()
    )
    documents = (
        db.query(Document)
        .filter(Document.status == "pending_review")
        .order_by(Document.created_at.desc())
        .all()
    )
    followups = (
        db.query(Followup)
        .filter(Followup.status == "pending_approval")
        .order_by(Followup.created_at.desc())
        .all()
    )

    return {
        "summaries": [
            {
                "id": s.id,
                "narrative_id": s.narrative_id,
                "flagged": s.flagged,
                "flag_reasons": s.flag_reasons,
                "interpretation_text": s.interpretation_text,
                "created_at": s.created_at,
            }
            for s in summaries
        ],
        "documents": [
            {
                "id": d.id,
                "patient_id": d.patient_id,
                "extracted_text": d.extracted_text,
                "hallucination_flagged": d.hallucination_flagged,
                "created_at": d.created_at,
            }
            for d in documents
        ],
        "followups": [
            {
                "id": f.id,
                "patient_id": f.patient_id,
                "query_text": f.query_text,
                "proposal_text": f.proposal_text,
                "created_at": f.created_at,
            }
            for f in followups
        ],
        "counts": {
            "summaries": len(summaries),
            "documents": len(documents),
            "followups": len(followups),
        },
    }
