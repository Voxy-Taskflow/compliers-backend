"""NLP Service: fact extraction from patient narrative transcript.
Uses Groq (free tier, OpenAI-compatible) instead of local Ollama - much faster,
no local GPU/CPU split issues. Swap back to Ollama by changing BASE_URL/MODEL if needed.
NEVER mixes interpretation/diagnosis language into this call - see interpretation.py for that (N-03).
"""
import json
from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key,  # add groq_api_key to your Settings/config in F-05
)

MODEL = "openai/gpt-oss-20b"  # replacement for deprecated llama-3.1-8b-instant (shut down 08/16/26)

FACT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "chief_complaint": {"type": ["string", "null"]},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "duration": {"type": ["string", "null"]},
        "severity": {"type": ["string", "null"]},
        "medications_mentioned": {"type": "array", "items": {"type": "string"}},
        "allergies_mentioned": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["symptoms", "medications_mentioned", "allergies_mentioned"],
}

SYSTEM_PROMPT = """You are a fact-extraction tool for a healthcare intake system.
Extract ONLY facts explicitly stated in the transcript. Do NOT infer, diagnose, or interpret.
If something is not mentioned, use null or an empty array - never guess or fill in plausible values.
Respond with ONLY a JSON object matching this schema, no prose, no markdown fences:

{schema}
"""


async def extract_facts(transcript_english: str) -> dict:
    prompt = SYSTEM_PROMPT.format(schema=json.dumps(FACT_EXTRACTION_SCHEMA, indent=2))

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Transcript:\n{transcript_english}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw_text = response.choices[0].message.content

    try:
        facts = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {raw_text[:200]}") from exc

    return facts
