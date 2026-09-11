"""NLP Service: schema validation + retry wrapper (N-04).
Wraps both fact_extraction.extract_facts and interpretation.interpret_facts.
On malformed/invalid output, retries once with a stricter reminder before giving up.
"""
import json
from typing import Awaitable, Callable, TypeVar

from jsonschema import validate, ValidationError

T = TypeVar("T")

MAX_RETRIES = 2

FACTS_SCHEMA = {
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

INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {
        "interpretation_text": {"type": "string"},
        "flagged_for_review": {"type": "boolean"},
        "flag_reason": {"type": ["string", "null"]},
    },
    "required": ["interpretation_text", "flagged_for_review"],
}


class NLPValidationError(Exception):
    """Raised when the model output fails schema validation after all retries."""


async def call_with_retry(
    fn: Callable[..., Awaitable[dict]],
    schema: dict,
    *args,
    **kwargs,
) -> dict:
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await fn(*args, **kwargs)
            validate(instance=result, schema=schema)
            return result
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            continue

    raise NLPValidationError(
        f"{fn.__name__} failed schema validation after {MAX_RETRIES} attempts: {last_error}"
    )
