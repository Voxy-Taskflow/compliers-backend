"""H-01 / H-02: Risk-gate rules + orchestration entry point.
Every AI-generated summary passes through here before hitting the DB.
Not fancy. One function, one call site. Add rules as list grows.
"""

EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "can't breathe", "unconscious",
    "severe bleeding", "suicidal", "suicide", "not breathing",
    "seizure", "stroke", "heart attack", "unresponsive",
]

LOW_CONFIDENCE_THRESHOLD = 0.6


def apply_risk_gate(facts: dict, interpretation: dict, transcript_confidence: float | None = None) -> dict:
    """Returns dict with flagged (bool) and flag_reasons (list or None)."""
    flags = []

    searchable_text = " ".join([
        interpretation.get("interpretation_text", ""),
        str(facts.get("chief_complaint", "")),
        " ".join(facts.get("symptoms", []) or []),
    ]).lower()

    if any(kw in searchable_text for kw in EMERGENCY_KEYWORDS):
        flags.append("emergency_keyword_detected")

    if transcript_confidence is not None and transcript_confidence < LOW_CONFIDENCE_THRESHOLD:
        flags.append("low_confidence_transcript")

    if interpretation.get("flagged_for_review"):
        flags.append(interpretation.get("flag_reason") or "model_self_flagged")

    return {
        "flagged": bool(flags),
        "flag_reasons": flags or None,
    }
