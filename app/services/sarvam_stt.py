"""Sarvam STT wrapper - low level HTTP call only. No DB, no orchestration here."""
import httpx

from app.core.config import get_settings

settings = get_settings()

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

# Path A: REST endpoint caps at 30s of audio. Enforce before we even call Sarvam,
# so we fail fast with a clear message instead of a confusing 422 from their side.
MAX_AUDIO_BYTES = 5 * 1024 * 1024  # ~5MB, generous ceiling for 30s of opus/webm audio


class SarvamSTTError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def transcribe_and_translate(audio_bytes: bytes, filename: str = "recording.webm") -> dict:
    """Send audio to Sarvam, get back English transcript + detected language.

    Returns dict: {transcript, detected_language, language_probability, request_id}
    Raises SarvamSTTError on any failure - caller decides what to do with it.
    """
    if not settings.sarvam_api_key:
        raise SarvamSTTError("SARVAM_API_KEY not configured - check .env")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise SarvamSTTError(
            f"Audio too large ({len(audio_bytes)} bytes) - likely over 30s cap for REST API"
        )

    if len(audio_bytes) == 0:
        raise SarvamSTTError("Empty audio file received")

    headers = {"api-subscription-key": settings.sarvam_api_key}
    files = {"file": (filename, audio_bytes, "audio/webm")}
    data = {
        "model": "saaras:v3",
        "mode": "translate",       # speech in any Indic language -> English text, one call
        "language_code": "unknown",  # let Sarvam auto-detect source language
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(SARVAM_STT_URL, headers=headers, data=data, files=files)
    except httpx.TimeoutException:
        raise SarvamSTTError("Sarvam API timed out - try again", status_code=504)
    except httpx.RequestError as e:
        raise SarvamSTTError(f"Network error calling Sarvam: {e}", status_code=502)

    if response.status_code != 200:
        raise SarvamSTTError(
            f"Sarvam API returned {response.status_code}: {response.text}",
            status_code=response.status_code,
        )

    body = response.json()
    return {
        "transcript": body.get("transcript", ""),
        "detected_language": body.get("language_code"),
        "language_probability": body.get("language_probability"),
        "request_id": body.get("request_id"),
    }
