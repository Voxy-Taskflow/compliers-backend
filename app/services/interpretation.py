"""NLP Service: interpretation of extracted facts (N-03).
DELIBERATELY SEPARATE from fact_extraction.py - never merge these calls or their outputs
into one prompt. This distinction is safety-critical: facts are neutral/verifiable,
interpretation is AI reasoning that must be visually and structurally distinct for staff review
(see S-01 split-pane UI). This output is also what gets fed into H-01 risk-gate rules
(diagnosis-like claims, conflicting history, etc).
"""
import json
from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,
)

MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are a clinical-context assistant helping a human reviewer understand a patient's
narrative facts. You are NOT diagnosing and NOT recommending treatment. Given a set of extracted facts,
write a short, plain-language interpretation that:
- Explains possible general contexts for the combination of symptoms (e.g. "fever with headache lasting
  several days is commonly associated with...")
- NEVER states a definitive diagnosis
- NEVER recommends a specific medication, dosage, or treatment
- Flags anything that seems urgent, unusual, or that conflicts within the facts given
- Is written for a HUMAN CLINICIAN to review, not the patient - do not soften into reassurance language

Respond with ONLY a JSON object: {"interpretation_text": "...", "flagged_for_review": true/false,
"flag_reason": "..." or null}
No markdown fences, no prose outside the JSON.
"""


async def interpret_facts(facts: dict) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extracted facts:\n{json.dumps(facts, indent=2)}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw_text = response.choices[0].message.content

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {raw_text[:200]}") from exc

    return result
