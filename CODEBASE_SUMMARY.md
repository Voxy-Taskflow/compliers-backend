# Healthcare Communication Assistant Backend — Codebase Summary

## 1. Project purpose

This backend powers a healthcare intake and review workflow for patient narratives, document OCR, AI-assisted summary generation, and human review/approval of follow-up actions. The system is structured as a FastAPI API layer with a PostgreSQL-backed SQLAlchemy data model and several external AI services for narrative analysis, OCR, and STT.

The app is designed around the following flow:

- Patient intake and narrative capture
- Optional audio-to-text transcription via Sarvam STT
- AI fact extraction and interpretation
- Risk gate evaluation for urgent or flagged cases
- Summary persistence with human review status
- OCR document ingestion and review workflow
- Follow-up proposal management requiring manual approval
- Review queue dashboard for staff triage

---

## 2. Stack and runtime

- Framework: FastAPI
- API server entry: `app/main.py`
- Database: PostgreSQL via SQLAlchemy ORM
- Migration tool: Alembic
- Package manager: `uv`
- LLM providers:
  - Groq via OpenAI-compatible API for fact extraction and interpretation
  - Google Gemini for OCR
- STT provider: Sarvam AI
- Config management: `app/core/config.py` using `pydantic_settings.BaseSettings`
- Auth: JWT-based middleware and demo token flow

Run command used by the project context:

```bash
uv run uvicorn app.main:app --reload
```

---

## 3. Core app entrypoints

### `app/main.py`

This is the main FastAPI application.

It:

- configures CORS
- adds `AuthMiddleware`
- registers app-level exception handlers
- exposes `/health`
- includes routers under the following prefixes:

```python
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(narratives.router, prefix="/narratives", tags=["narratives"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(followups.router, prefix="/followups", tags=["followups"])
app.include_router(review_queue.router, prefix="/review-queue", tags=["review-queue"])
app.include_router(summaries.router)  # prefix built in: /narratives
app.include_router(summaries.summaries_router)  # prefix built in: /summaries
```

Important convention:

- There are two router areas in this codebase: `app/api/routes/` and `app/routers/`
- The active implementation for narratives/summaries/followups lives primarily under `app/routers/`
- `app/api/routes/narratives.py` is a placeholder and is not the real implementation

---

## 4. Router layout and responsibilities

### `app/api/routes/`

This is the original scaffold and includes some still-active modules but also placeholders.

Files:

- `auth.py` — auth routes and demo login
- `documents.py` — real document upload/OCR/list/get/review routes
- `review_queue.py` — aggregate review queue endpoint
- `followups.py` — placeholder route stub
- `narratives.py` — dead placeholder

### `app/routers/`

This is where the active production-like flows live.

Files:

- `narratives.py` — narrative creation from text and voice transcription flow
- `summaries.py` — narrative summarization, summary listing, summary review
- `followups.py` — follow-up create/list/get/approve/reject endpoints

### Route summary

#### Narrative routes

- `POST /narratives/` — create narrative from transcript text
- `POST /narratives/voice` — create narrative from uploaded audio using Sarvam STT
- `GET /narratives/` — alive/health-like placeholder route

#### Summary routes

- `POST /narratives/{narrative_id}/summarize` — runs fact extraction + interpretation + validation + risk gate and stores a summary in `pending_review`
- `GET /summaries/` — list summaries with optional filters
- `GET /summaries/{summary_id}` — fetch one summary
- `POST /summaries/{summary_id}/review` — set summary review decision (`reviewed`, `actioned`, `rejected`)

#### Followup routes

- `POST /followups/` — create follow-up proposal
- `GET /followups/` and `/followups/list` — list follow-ups
- `GET /followups/{followup_id}` — fetch one
- `POST /followups/{followup_id}/approve` — mark approved
- `POST /followups/{followup_id}/reject` — mark rejected

#### Documents routes

- `GET /documents/` — list documents
- `POST /documents/upload` — upload image, store locally, run OCR
- `GET /documents/{document_id}` — fetch one
- `POST /documents/{document_id}/review` — review decision

#### Review queue

- `GET /review-queue/` — aggregate pending review items across summaries, documents, and follow-ups

---

## 5. Database model and schema

The SQLAlchemy model in `app/db/models.py` is meant to mirror the Alembic schema in `migrations/versions/0001_initial_schema.py` exactly.

### Core tables

#### `Staff`

- Fields: `id`, `created_at`, `name`, `email`, `phone`, `role`, `password_hash`, `is_active`
- `role` is constrained to: `reviewer | admin | super_admin`
- This table is largely empty in dev; there is a throwaway demo row used during smoke tests

#### `Patient`

- Fields include patient metadata and relationships
- One patient can have many narratives, documents, and follow-ups

#### `Narrative`

- Status values: `captured | confirmed | discarded`
- Stores transcript text, detected language, confidence, and optional `audio_ref`

#### `Summary`

- Status values: `pending_review | reviewed | actioned | rejected`
- Stores `facts_json`, `interpretation_text`, `flagged`, `flag_reasons`, `reviewed_by`, `reviewed_at`
- `flagged` is a boolean risk signal generated by `apply_risk_gate`

#### `Document`

- Status values: same as `Summary`
- Stores OCR output and metadata
- Unlike `Summary`, it does not currently have `reviewed_by` / `reviewed_at`

#### `Followup`

- Status values: `pending_approval | approved | rejected | scheduled`
- Supports `approved_by`, `approved_at`, `query_text`, `rag_context`, `proposal_text`, `calendar_event_id`

#### `AuditLog`

- Table exists and supports actor-based audit entries
- `actor_type` values: `ai | staff | patient | system`
- Current codebase does not write to this table yet

---

## 6. Key services

### `app/services/fact_extraction.py`

- Calls Groq with an OpenAI-compatible client
- Extracts facts from patient transcript
- Uses schema-driven JSON output
- Raises a generic `ValueError` when output is not valid JSON

### `app/services/interpretation.py`

- Separate AI call from fact extraction
- Produces a plain-language interpretation for clinician review
- Returns:

```python
{
  "interpretation_text": "...",
  "flagged_for_review": true,
  "flag_reason": "..." or null
}
```

### `app/services/nlp_validation.py`

- Wraps both model outputs with `jsonschema` validation
- Re-attempts failed outputs up to `MAX_RETRIES = 2`
- Raises `NLPValidationError` when validation ultimately fails

### `app/services/risk_gate.py`

- Applies risk detection based on:
  - emergency keywords
  - low transcript confidence
  - model self-flagging from the interpretation step
- Returns:

```python
{
  "flagged": bool,
  "flag_reasons": list[str] | None,
}
```

### `app/services/ocr_service.py`

- Uses Google Gemini OCR via `google-genai`
- Accepts image bytes and MIME type
- Returns raw extracted text from the image
- Raises `OCRError` on failure

### `app/services/sarvam_stt.py`

- Pure HTTP wrapper to Sarvam STT
- Accepts audio, sends to `speech-to-text` endpoint, returns transcript and language metadata
- Raises `SarvamSTTError` with status code when request fails

---

## 7. Config and auth

### `app/core/config.py`

- Uses `pydantic_settings.BaseSettings`
- Reads `.env`
- Provides `get_settings()` via `lru_cache`
- Includes keys for:
  - database URL
  - JWT secret and algorithm
  - OCR API key
  - Groq API key
  - Sarvam API key
  - Google Calendar settings
  - CORS origins

### `app/middleware/auth.py`

- Middleware checks bearer tokens on almost all routes
- Publishes public paths like `/health`, `/auth/dev-login`, `/docs`, etc.
- Stores payload claims on `request.state`
- Current implementation is a placeholder demo auth layer rather than a full staff identity system

### `app/api/routes/auth.py`

- Exposes `/auth/dev-login`
- Generates a JWT using the configured secret
- This is explicitly a demo shortcut, not real production auth

---

## 8. Data flow and business logic

### Narrative creation flow

1. Client posts transcript text or audio to narrative route
2. Narrative row is created in DB
3. Summary flow can later call NLP pipeline on `transcript_english`

### Summary pipeline

The summary endpoint in `app/routers/summaries.py` does the following:

1. loads a narrative
2. verifies transcript exists
3. `call_with_retry(extract_facts, FACTS_SCHEMA, transcript)`
4. `call_with_retry(interpret_facts, INTERPRETATION_SCHEMA, facts)`
5. `apply_risk_gate(facts, interpretation, confidence)`
6. creates `Summary` row with `status="pending_review"`
7. returns serialized summary payload

This is the main AI orchestration path and is considered one of the critical working flows in the codebase.

### Follow-up lifecycle

- A follow-up is created with `proposal_text` supplied directly by the caller
- It starts in `pending_approval`
- Staff can approve or reject by passing a `staff_id`
- No real auth or RAG generation is yet integrated

### Document OCR lifecycle

- Upload image via `POST /documents/upload`
- Save to `uploads/documents/`
- Run OCR model
- Save document row with `status="pending_review"`
- Human review action updates document status

---

## 9. Important conventions and gotchas

### Router duplication risk

There are two router directories and they can easily create duplicate or conflicting routes.

- `app/api/routes/` contains some active and placeholder routes
- `app/routers/` contains the real active endpoint implementations

This mismatch has already caused real bugs in the project history, so route additions should be checked in both locations before editing.

### Summary/router prefix gotcha

In `app/routers/summaries.py` there are two APIRouters:

- `router` with prefix `/narratives`
- `summaries_router` with prefix `/summaries`

Both must be included separately in `main.py`.

### Model-migration parity

The model file is intentionally expected to match the schema in the migration file exactly. If the ORM model changes, a new Alembic migration should also be written.

---

## 10. Known issues and incomplete work

The project notes identify several real gaps:

1. Encoding bug for non-ASCII text
   - Malayalam or smart-quote content is reportedly mangled across the pipeline
   - Likely suspects include HTTP JSON decoding or database encoding configuration

2. No real staff authentication
   - `staff_id` is passed in request bodies as a placeholder
   - no direct JWT-to-DB mapping exists

3. JWT secret is insecure default
   - Config currently uses `"change-me-in-real-env"`
   - This is fine for dev but not production-safe

4. AuditLog is not used
   - Schema exists, but nothing writes to it yet

5. RAG is not implemented for follow-ups
   - `proposal_text` is still supplied directly by the caller

6. Google Calendar integration is not implemented
   - `calendar_event_id` exists but no API call is wired in

7. No pagination on list endpoints
   - All list routes return the full set of rows

8. `POST /narratives/voice` does not persist audio to disk
   - `audio_ref` is set to `None` in the current implementation, despite the schema supporting it

9. Unused or dead placeholder files exist
   - `app/api/routes/narratives.py` is a dead placeholder
   - `app/api/routes/followups.py` is also just a stub

---

## 11. What is built and working

The codebase context describes the following as already working this session:

- Document upload → OCR → DB write
- Narrative creation from text
- Full narrative summarization pipeline with risk gate and summary persistence
- Follow-up create → list → get → approve/reject flow
- Review queue aggregate endpoint

This indicates the backend has a functioning core workflow for AI-assisted clinical intake review, even though some polish and production-hardening work remains.

---

## 12. Current repository structure

```text
comiplers-backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── documents.py
│   │       ├── followups.py
│   │       ├── narratives.py
│   │       └── review_queue.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── middleware/
│   │   └── auth.py
│   ├── models/
│   │   ├── audit_log.py
│   │   ├── document.py
│   │   ├── followup.py
│   │   ├── mixins.py
│   │   ├── narrative.py
│   │   ├── patient.py
│   │   ├── staff.py
│   │   ├── summary.py
│   │   └── __init__.py
│   ├── routers/
│   │   ├── followups.py
│   │   ├── narratives.py
│   │   ├── summaries.py
│   │   └── __init__.py
│   ├── schemas/
│   ├── services/
│   │   ├── fact_extraction.py
│   │   ├── interpretation.py
│   │   ├── nlp_validation.py
│   │   ├── ocr_service.py
│   │   ├── risk_gate.py
│   │   └── sarvam_stt.py
│   └── main.py
├── data/
│   └── audio/
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
├── scripts/
│   └── setup_f03.ps1
├── tests/
│   └── __init__.py
├── uploads/
│   └── documents/
├── README.md
├── main.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
├── add_migration.ps1
└── .env (if configured locally)
```

---

## 13. Recommended next steps

The project notes suggest the following priorities:

1. Root-cause the text encoding bug
2. Smoke-test untested endpoints like document list/get and voice transcription
3. Replace placeholder `staff_id` approval logic with real staff auth
4. Add `AuditLog` writes to review/approve actions
5. Decide whether raw audio files should be retained permanently
6. Harden app configuration for production secrets and environment-specific settings

---

## 14. Bottom line

This codebase is a working healthcare intake/review API prototype with a clean conceptual flow, a real SQLAlchemy schema, and active AI-backed service calls for summary generation and OCR. The biggest risks are not missing basic endpoints, but rather production-hardening gaps: missing real identity/auth, incomplete audit trail, placeholder behavior around follow-up generation, and unresolved encoding problems. The backend is clearly in an active development stage rather than a finished production system.
