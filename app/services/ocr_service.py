"""D-02: Document Service wrapper for OCR via Google AI Studio (Gemini vision).
Takes raw image bytes, returns extracted text. Preprocessing (deskew/contrast)
left as TODO stretch - not blocking for demo, real OCR quality first.
"""
from google import genai
from google.genai import types

from app.core.config import get_settings

OCR_PROMPT = (
    "Extract all text visible in this image exactly as written. "
    "This is a medical document (prescription, lab report, or discharge note). "
    "Preserve line breaks. Do not summarize, interpret, or add anything. "
    "Return ONLY the raw extracted text, nothing else."
)


class OCRError(Exception):
    pass


async def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    try:
        settings = get_settings()
        client = genai.Client(api_key=settings.google_ai_studio_api_key)

        response = client.models.generate_content(
    model="gemini-flash-latest",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        OCR_PROMPT,
    ],
)
        text = response.text
        if not text or not text.strip():
            raise OCRError("OCR returned empty text - image may be unreadable")
        return text.strip()
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(f"OCR extraction failed: {exc}") from exc