"""Route: trigger NLP summarization for a captured narrative (N-05).
Wires: Narrative.transcript_english -> fact_extraction + interpretation (N-01/02/03)
-> schema validation with retry (N-04) -> risk-gate (H-01/H-02) -> Summary row,
status ALWAYS "pending_review" (H-03). No auto-finalization path exists here.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Narrative, Summary
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

    return {
        "id": summary.id,
        "narrative_id": summary.narrative_id,
        "status": summary.status,
        "facts_json": summary.facts_json,
        "interpretation_text": summary.interpretation_text,
        "flagged": summary.flagged,
        "flag_reasons": summary.flag_reasons,
        "created_at": summary.created_at,
    }
