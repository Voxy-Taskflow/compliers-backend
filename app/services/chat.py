"""NLP Service: Chat completion for patient follow-up questions.
Uses Groq to generate fact-based answers grounded in the patient's context.
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

SYSTEM_PROMPT = """You are a clinical assistant answering a patient's follow-up question.
You are given the patient's clinical context (e.g. recent symptoms, extracted facts, medications) and their question.
You must provide:
1. 'factContent': A brief, 1-2 sentence statement of the relevant fact from their context (e.g. "From your consultation records: you reported chest heaviness...").
2. 'aiContent': Your advice or answer to their question based on those facts.

RULES:
- NEVER state a definitive diagnosis.
- NEVER recommend a specific new medication or dosage.
- If the question indicates a medical emergency, advise them to call emergency services immediately.
- Use clear, simple, reassuring language.
- Respond with ONLY a JSON object: {"factContent": "...", "aiContent": "..."}
- No markdown fences, no prose outside the JSON.
"""


async def generate_chat_response(context: dict, query: str) -> dict:
    context_str = json.dumps(context, indent=2) if context else "No prior medical context available."
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Clinical Context:\n{context_str}\n\nPatient Question: {query}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw_text = response.choices[0].message.content

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {raw_text[:200]}") from exc

    return result
